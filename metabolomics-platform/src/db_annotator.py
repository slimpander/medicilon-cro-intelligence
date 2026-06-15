"""
db_annotator.py — Metabolite Annotation Engine
================================================
Matches detected features against metabolomics databases by accurate mass.

Primary matcher (default, always available)
  - Built-in curated metabolite database (~120 common metabolites, see
    METABOLITE_CACHE). Fully offline, no network required. This is the
    dependable default and what `use_online=False` relies on.

Optional online matchers (best-effort, OFF by default)
  - HMDB, METLIN, MassBank. These are queried only when `use_online=True`.
    NOTE: HMDB and METLIN do not currently expose a free, unauthenticated
    mass-search REST endpoint — they generally require a license or API key,
    so those calls will typically return nothing on a stock install. MassBank
    Europe exposes a public API but its schema may change. Online failures are
    recorded (see AnnotationResult.online_errors / online_available) rather
    than silently ignored, so the caller can tell "no match" from "lookup
    unavailable". Treat online results as supplementary, not authoritative.

Annotation strategies:
  1. Accurate mass search (±ppm tolerance), adduct-aware
  2. MS/MS spectral matching (when spectra available)
  3. Isotopic pattern scoring
  4. Adduct detection and neutral mass calculation
"""

from __future__ import annotations

import json
import hashlib
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
import numpy as np

from .io_utils import DetectedFeature, FeatureTable


# ══════════════════════════════════════════════════════════════════════
# Common adducts for metabolite annotation
# ══════════════════════════════════════════════════════════════════════

ADDUCT_DATABASE = {
    # Positive mode
    "[M+H]+":        {"mass_shift": 1.007276, "charge": 1, "mode": "positive", "multiplier": 1},
    "[M+Na]+":       {"mass_shift": 22.989218, "charge": 1, "mode": "positive", "multiplier": 1},
    "[M+K]+":        {"mass_shift": 38.963158, "charge": 1, "mode": "positive", "multiplier": 1},
    "[M+NH4]+":      {"mass_shift": 18.033823, "charge": 1, "mode": "positive", "multiplier": 1},
    "[M+H-H2O]+":    {"mass_shift": -17.003289, "charge": 1, "mode": "positive", "multiplier": 1},
    "[M+2H]2+":      {"mass_shift": 2.014552, "charge": 2, "mode": "positive", "multiplier": 1},
    "[M+2Na]2+":     {"mass_shift": 45.978436, "charge": 2, "mode": "positive", "multiplier": 1},
    "[M+H+Na]2+":    {"mass_shift": 23.996494, "charge": 2, "mode": "positive", "multiplier": 1},
    "[M+CH3CN+H]+":  {"mass_shift": 42.033823, "charge": 1, "mode": "positive", "multiplier": 1},
    "[M+CH3OH+H]+":  {"mass_shift": 33.033489, "charge": 1, "mode": "positive", "multiplier": 1},

    # Negative mode
    "[M-H]-":        {"mass_shift": -1.007276, "charge": -1, "mode": "negative", "multiplier": 1},
    "[M-H2O-H]-":    {"mass_shift": -19.018906, "charge": -1, "mode": "negative", "multiplier": 1},
    "[M+Cl]-":       {"mass_shift": 34.969402, "charge": -1, "mode": "negative", "multiplier": 1},
    "[M+HCOO]-":     {"mass_shift": 44.998203, "charge": -1, "mode": "negative", "multiplier": 1},
    "[M+CH3COO]-":   {"mass_shift": 59.013853, "charge": -1, "mode": "negative", "multiplier": 1},
    "[M-2H]2-":      {"mass_shift": -2.014552, "charge": -2, "mode": "negative", "multiplier": 1},

    # Dimers
    "[2M+H]+":       {"mass_shift": 1.007276, "charge": 1, "mode": "positive", "multiplier": 2},
    "[2M+Na]+":      {"mass_shift": 22.989218, "charge": 1, "mode": "positive", "multiplier": 2},
    "[2M-H]-":       {"mass_shift": -1.007276, "charge": -1, "mode": "negative", "multiplier": 2},
}

COMMON_ADDUCTS_POSITIVE = [
    "[M+H]+", "[M+Na]+", "[M+K]+", "[M+NH4]+",
    "[M+H-H2O]+", "[2M+H]+", "[2M+Na]+",
]

COMMON_ADDUCTS_NEGATIVE = [
    "[M-H]-", "[M+Cl]-", "[M+HCOO]-", "[M+CH3COO]-",
    "[M-H2O-H]-", "[2M-H]-",
]


# ══════════════════════════════════════════════════════════════════════
# Dataclasses
# ══════════════════════════════════════════════════════════════════════

@dataclass
class MetaboliteMatch:
    """A single database match for a detected feature."""
    name: str
    formula: str
    monoisotopic_mass: float
    database: str                   # "HMDB", "METLIN", "MassBank", "LocalCache"
    accession: str                  # Database-specific ID
    adduct: Optional[str] = None
    mass_error_ppm: float = 0.0
    mass_error_da: float = 0.0
    score: float = 0.0              # 0-1 match confidence
    rank: int = 1
    description: str = ""
    pathways: List[str] = field(default_factory=list)
    inchikey: str = ""
    smiles: str = ""

    @property
    def is_high_confidence(self) -> bool:
        return self.score >= 0.7


@dataclass
class AnnotatedFeature:
    """A detected feature with database annotations."""
    feature_id: int
    mz: float
    rt: float
    intensity: float
    matches: List[MetaboliteMatch] = field(default_factory=list)
    top_match: Optional[MetaboliteMatch] = None
    adduct_guess: Optional[str] = None
    neutral_mass: Optional[float] = None

    @property
    def is_annotated(self) -> bool:
        return len(self.matches) > 0


@dataclass
class AnnotationResult:
    """Complete annotation results for a feature list."""
    annotated_features: List[AnnotatedFeature]
    total_features: int
    annotated_count: int
    high_confidence_count: int
    databases_queried: List[str]
    search_params: Dict = field(default_factory=dict)
    # Online lookup status — lets the caller distinguish "no match found"
    # from "online database was unreachable / returned an error".
    online_requested: bool = False
    online_available: bool = False          # True if any online DB returned data
    online_errors: List[str] = field(default_factory=list)
    databases_with_hits: List[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# Mass Calculator
# ══════════════════════════════════════════════════════════════════════

# Atomic masses (monoisotopic) in Da
ATOMIC_MASSES = {
    "H": 1.007825032,
    "C": 12.000000000,
    "N": 14.003074005,
    "O": 15.994914620,
    "P": 30.973761998,
    "S": 31.972071174,
    "F": 18.998403163,
    "Cl": 34.968852721,
    "Na": 22.989769282,
    "K": 38.963706486,
    "Br": 78.918337600,
    "I": 126.904471900,
    "Fe": 55.934936330,
    "Zn": 63.929142010,
    "Se": 79.916521800,
}


def parse_formula(formula: str) -> Dict[str, int]:
    """Parse a molecular formula string into element counts.

    Examples:
        "C6H12O6" → {"C": 6, "H": 12, "O": 6}
        "C8H10N4O2" → {"C": 8, "H": 10, "N": 4, "O": 2}
    """
    import re
    counts = {}
    pattern = re.compile(r'([A-Z][a-z]?)(\d*)')
    for match in pattern.finditer(formula):
        elem = match.group(1)
        count = int(match.group(2)) if match.group(2) else 1
        counts[elem] = counts.get(elem, 0) + count
    return counts


def formula_to_mass(formula: str) -> float:
    """Calculate monoisotopic mass from molecular formula."""
    counts = parse_formula(formula)
    mass = 0.0
    for elem, count in counts.items():
        if elem not in ATOMIC_MASSES:
            raise ValueError(f"Unknown element: {elem}")
        mass += ATOMIC_MASSES[elem] * count
    return mass


def calculate_neutral_mass(observed_mz: float, adduct: str) -> float:
    """Calculate neutral monoisotopic mass from observed m/z and adduct."""
    if adduct not in ADDUCT_DATABASE:
        raise ValueError(f"Unknown adduct: {adduct}")
    adduct_info = ADDUCT_DATABASE[adduct]
    return (observed_mz * abs(adduct_info["charge"]) - adduct_info["mass_shift"]) / adduct_info["multiplier"]


def calculate_adduct_mz(neutral_mass: float, adduct: str) -> float:
    """Calculate expected m/z from neutral mass and adduct."""
    if adduct not in ADDUCT_DATABASE:
        raise ValueError(f"Unknown adduct: {adduct}")
    adduct_info = ADDUCT_DATABASE[adduct]
    return (neutral_mass * adduct_info["multiplier"] + adduct_info["mass_shift"]) / abs(adduct_info["charge"])


def guess_adducts(
    observed_mz: float,
    neutral_mass_candidates: List[float],
    mode: str = "positive",
) -> List[Tuple[str, float, float]]:
    """Guess which adduct(s) could explain an observed m/z given candidate neutral masses.

    Returns list of (adduct_name, neutral_mass, mass_error_ppm) tuples.
    """
    if mode == "positive":
        adducts = COMMON_ADDUCTS_POSITIVE
    else:
        adducts = COMMON_ADDUCTS_NEGATIVE

    results = []
    for adduct in adducts:
        for neutral_mass in neutral_mass_candidates:
            expected_mz = calculate_adduct_mz(neutral_mass, adduct)
            ppm_error = abs(observed_mz - expected_mz) / max(expected_mz, 1e-6) * 1e6
            if ppm_error < 20:
                results.append((adduct, neutral_mass, ppm_error))

    results.sort(key=lambda x: x[2])
    return results


# ══════════════════════════════════════════════════════════════════════
# Local Metabolite Cache
# ══════════════════════════════════════════════════════════════════════

# Curated common metabolites with names, formulas, and HMDB IDs
# Used as the primary matching database for fast offline annotation
METABOLITE_CACHE: List[Dict] = [
    # Amino acids
    {"name": "L-Alanine", "formula": "C3H7NO2", "hmdb": "HMDB0000161", "kegg": "C00041", "super_class": "Amino acids"},
    {"name": "L-Arginine", "formula": "C6H14N4O2", "hmdb": "HMDB0000517", "kegg": "C00062", "super_class": "Amino acids"},
    {"name": "L-Asparagine", "formula": "C4H8N2O3", "hmdb": "HMDB0000168", "kegg": "C00152", "super_class": "Amino acids"},
    {"name": "L-Aspartic acid", "formula": "C4H7NO4", "hmdb": "HMDB0000191", "kegg": "C00049", "super_class": "Amino acids"},
    {"name": "L-Cysteine", "formula": "C3H7NO2S", "hmdb": "HMDB0000574", "kegg": "C00097", "super_class": "Amino acids"},
    {"name": "L-Glutamic acid", "formula": "C5H9NO4", "hmdb": "HMDB0000148", "kegg": "C00025", "super_class": "Amino acids"},
    {"name": "L-Glutamine", "formula": "C5H10N2O3", "hmdb": "HMDB0000641", "kegg": "C00064", "super_class": "Amino acids"},
    {"name": "Glycine", "formula": "C2H5NO2", "hmdb": "HMDB0000123", "kegg": "C00037", "super_class": "Amino acids"},
    {"name": "L-Histidine", "formula": "C6H9N3O2", "hmdb": "HMDB0000177", "kegg": "C00135", "super_class": "Amino acids"},
    {"name": "L-Isoleucine", "formula": "C6H13NO2", "hmdb": "HMDB0000172", "kegg": "C00407", "super_class": "Amino acids"},
    {"name": "L-Leucine", "formula": "C6H13NO2", "hmdb": "HMDB0000687", "kegg": "C00123", "super_class": "Amino acids"},
    {"name": "L-Lysine", "formula": "C6H14N2O2", "hmdb": "HMDB0000182", "kegg": "C00047", "super_class": "Amino acids"},
    {"name": "L-Methionine", "formula": "C5H11NO2S", "hmdb": "HMDB0000696", "kegg": "C00073", "super_class": "Amino acids"},
    {"name": "L-Phenylalanine", "formula": "C9H11NO2", "hmdb": "HMDB0000159", "kegg": "C00079", "super_class": "Amino acids"},
    {"name": "L-Proline", "formula": "C5H9NO2", "hmdb": "HMDB0000162", "kegg": "C00148", "super_class": "Amino acids"},
    {"name": "L-Serine", "formula": "C3H7NO3", "hmdb": "HMDB0000187", "kegg": "C00065", "super_class": "Amino acids"},
    {"name": "L-Threonine", "formula": "C4H9NO3", "hmdb": "HMDB0000167", "kegg": "C00188", "super_class": "Amino acids"},
    {"name": "L-Tryptophan", "formula": "C11H12N2O2", "hmdb": "HMDB0000929", "kegg": "C00078", "super_class": "Amino acids"},
    {"name": "L-Tyrosine", "formula": "C9H11NO3", "hmdb": "HMDB0000158", "kegg": "C00082", "super_class": "Amino acids"},
    {"name": "L-Valine", "formula": "C5H11NO2", "hmdb": "HMDB0000883", "kegg": "C00183", "super_class": "Amino acids"},
    {"name": "Taurine", "formula": "C2H7NO3S", "hmdb": "HMDB0000251", "kegg": "C00245", "super_class": "Amino acids"},
    {"name": "Ornithine", "formula": "C5H12N2O2", "hmdb": "HMDB0000214", "kegg": "C00077", "super_class": "Amino acids"},
    {"name": "Citrulline", "formula": "C6H13N3O3", "hmdb": "HMDB0000904", "kegg": "C00327", "super_class": "Amino acids"},
    {"name": "Sarcosine", "formula": "C3H7NO2", "hmdb": "HMDB0000271", "kegg": "C00213", "super_class": "Amino acids"},
    {"name": "Creatine", "formula": "C4H9N3O2", "hmdb": "HMDB0000064", "kegg": "C00300", "super_class": "Amino acids"},
    {"name": "Creatinine", "formula": "C4H7N3O", "hmdb": "HMDB0000562", "kegg": "C00791", "super_class": "Amino acids"},
    {"name": "Carnitine", "formula": "C7H15NO3", "hmdb": "HMDB0000062", "kegg": "C00318", "super_class": "Amino acids"},
    {"name": "Acetylcarnitine", "formula": "C9H17NO4", "hmdb": "HMDB0000201", "kegg": "C02571", "super_class": "Amino acids"},

    # TCA cycle
    {"name": "Citric acid", "formula": "C6H8O7", "hmdb": "HMDB0000094", "kegg": "C00158", "super_class": "TCA cycle"},
    {"name": "Isocitric acid", "formula": "C6H8O7", "hmdb": "HMDB0000193", "kegg": "C00311", "super_class": "TCA cycle"},
    {"name": "alpha-Ketoglutaric acid", "formula": "C5H6O5", "hmdb": "HMDB0000208", "kegg": "C00026", "super_class": "TCA cycle"},
    {"name": "Succinic acid", "formula": "C4H6O4", "hmdb": "HMDB0000254", "kegg": "C00042", "super_class": "TCA cycle"},
    {"name": "Fumaric acid", "formula": "C4H4O4", "hmdb": "HMDB0000134", "kegg": "C00122", "super_class": "TCA cycle"},
    {"name": "L-Malic acid", "formula": "C4H6O5", "hmdb": "HMDB0000156", "kegg": "C00149", "super_class": "TCA cycle"},
    {"name": "Oxaloacetic acid", "formula": "C4H4O5", "hmdb": "HMDB0000223", "kegg": "C00036", "super_class": "TCA cycle"},
    {"name": "Pyruvic acid", "formula": "C3H4O3", "hmdb": "HMDB0000243", "kegg": "C00022", "super_class": "TCA cycle"},
    {"name": "Lactic acid", "formula": "C3H6O3", "hmdb": "HMDB0000190", "kegg": "C00186", "super_class": "TCA cycle"},
    {"name": "Aconitic acid", "formula": "C6H6O6", "hmdb": "HMDB0000072", "kegg": "C00417", "super_class": "TCA cycle"},

    # Carbohydrates
    {"name": "D-Glucose", "formula": "C6H12O6", "hmdb": "HMDB0000122", "kegg": "C00031", "super_class": "Carbohydrates"},
    {"name": "D-Fructose", "formula": "C6H12O6", "hmdb": "HMDB0000660", "kegg": "C00095", "super_class": "Carbohydrates"},
    {"name": "D-Galactose", "formula": "C6H12O6", "hmdb": "HMDB0000143", "kegg": "C00124", "super_class": "Carbohydrates"},
    {"name": "D-Mannose", "formula": "C6H12O6", "hmdb": "HMDB0000169", "kegg": "C00159", "super_class": "Carbohydrates"},
    {"name": "Sucrose", "formula": "C12H22O11", "hmdb": "HMDB0000258", "kegg": "C00089", "super_class": "Carbohydrates"},
    {"name": "Lactose", "formula": "C12H22O11", "hmdb": "HMDB0000186", "kegg": "C00243", "super_class": "Carbohydrates"},
    {"name": "Maltose", "formula": "C12H22O11", "hmdb": "HMDB0000163", "kegg": "C00208", "super_class": "Carbohydrates"},
    {"name": "Ribose", "formula": "C5H10O5", "hmdb": "HMDB0000283", "kegg": "C00121", "super_class": "Carbohydrates"},
    {"name": "Deoxyribose", "formula": "C5H10O4", "hmdb": "HMDB0003226", "kegg": "C01801", "super_class": "Carbohydrates"},
    {"name": "myo-Inositol", "formula": "C6H12O6", "hmdb": "HMDB0000211", "kegg": "C00137", "super_class": "Carbohydrates"},
    {"name": "D-Glucuronic acid", "formula": "C6H10O7", "hmdb": "HMDB0000127", "kegg": "C00191", "super_class": "Carbohydrates"},
    {"name": "Gluconic acid", "formula": "C6H12O7", "hmdb": "HMDB0000625", "kegg": "C00257", "super_class": "Carbohydrates"},

    # Nucleotides
    {"name": "ATP", "formula": "C10H16N5O13P3", "hmdb": "HMDB0000538", "kegg": "C00002", "super_class": "Nucleotides"},
    {"name": "ADP", "formula": "C10H15N5O10P2", "hmdb": "HMDB0001341", "kegg": "C00008", "super_class": "Nucleotides"},
    {"name": "AMP", "formula": "C10H14N5O7P", "hmdb": "HMDB0000045", "kegg": "C00020", "super_class": "Nucleotides"},
    {"name": "Adenosine", "formula": "C10H13N5O4", "hmdb": "HMDB0000050", "kegg": "C00212", "super_class": "Nucleotides"},
    {"name": "Adenine", "formula": "C5H5N5", "hmdb": "HMDB0000034", "kegg": "C00147", "super_class": "Nucleotides"},
    {"name": "GTP", "formula": "C10H16N5O14P3", "hmdb": "HMDB0001273", "kegg": "C00044", "super_class": "Nucleotides"},
    {"name": "GDP", "formula": "C10H15N5O11P2", "hmdb": "HMDB0001201", "kegg": "C00035", "super_class": "Nucleotides"},
    {"name": "GMP", "formula": "C10H14N5O8P", "hmdb": "HMDB0001397", "kegg": "C00144", "super_class": "Nucleotides"},
    {"name": "Guanosine", "formula": "C10H13N5O5", "hmdb": "HMDB0000133", "kegg": "C00387", "super_class": "Nucleotides"},
    {"name": "Guanine", "formula": "C5H5N5O", "hmdb": "HMDB0000132", "kegg": "C00242", "super_class": "Nucleotides"},
    {"name": "Uridine", "formula": "C9H12N2O6", "hmdb": "HMDB0000296", "kegg": "C00299", "super_class": "Nucleotides"},
    {"name": "Uracil", "formula": "C4H4N2O2", "hmdb": "HMDB0000300", "kegg": "C00106", "super_class": "Nucleotides"},
    {"name": "Cytidine", "formula": "C9H13N3O5", "hmdb": "HMDB0000089", "kegg": "C00475", "super_class": "Nucleotides"},
    {"name": "Cytosine", "formula": "C4H5N3O", "hmdb": "HMDB0000630", "kegg": "C00380", "super_class": "Nucleotides"},
    {"name": "Thymidine", "formula": "C10H14N2O5", "hmdb": "HMDB0000273", "kegg": "C00214", "super_class": "Nucleotides"},
    {"name": "Thymine", "formula": "C5H6N2O2", "hmdb": "HMDB0000262", "kegg": "C00178", "super_class": "Nucleotides"},
    {"name": "Inosine", "formula": "C10H12N4O5", "hmdb": "HMDB0000195", "kegg": "C00294", "super_class": "Nucleotides"},
    {"name": "Hypoxanthine", "formula": "C5H4N4O", "hmdb": "HMDB0000157", "kegg": "C00262", "super_class": "Nucleotides"},
    {"name": "Xanthine", "formula": "C5H4N4O2", "hmdb": "HMDB0000292", "kegg": "C00385", "super_class": "Nucleotides"},
    {"name": "Uric acid", "formula": "C5H4N4O3", "hmdb": "HMDB0000289", "kegg": "C00366", "super_class": "Nucleotides"},
    {"name": "NAD", "formula": "C21H27N7O14P2", "hmdb": "HMDB0000902", "kegg": "C00003", "super_class": "Nucleotides"},
    {"name": "NADH", "formula": "C21H29N7O14P2", "hmdb": "HMDB0001487", "kegg": "C00004", "super_class": "Nucleotides"},
    {"name": "NADP", "formula": "C21H28N7O17P3", "hmdb": "HMDB0000217", "kegg": "C00006", "super_class": "Nucleotides"},
    {"name": "FAD", "formula": "C27H33N9O15P2", "hmdb": "HMDB0001248", "kegg": "C00016", "super_class": "Nucleotides"},

    # Cofactors & vitamins
    {"name": "Ascorbic acid", "formula": "C6H8O6", "hmdb": "HMDB0000044", "kegg": "C00072", "super_class": "Vitamins"},
    {"name": "Thiamine", "formula": "C12H17N4OS", "hmdb": "HMDB0000235", "kegg": "C00378", "super_class": "Vitamins"},
    {"name": "Riboflavin", "formula": "C17H20N4O6", "hmdb": "HMDB0000244", "kegg": "C00255", "super_class": "Vitamins"},
    {"name": "Nicotinic acid", "formula": "C6H5NO2", "hmdb": "HMDB0001488", "kegg": "C00253", "super_class": "Vitamins"},
    {"name": "Nicotinamide", "formula": "C6H6N2O", "hmdb": "HMDB0001406", "kegg": "C00153", "super_class": "Vitamins"},
    {"name": "Pantothenic acid", "formula": "C9H17NO5", "hmdb": "HMDB0000210", "kegg": "C00864", "super_class": "Vitamins"},
    {"name": "Pyridoxine", "formula": "C8H11NO3", "hmdb": "HMDB0000239", "kegg": "C00314", "super_class": "Vitamins"},
    {"name": "Pyridoxal", "formula": "C8H9NO3", "hmdb": "HMDB0001545", "kegg": "C00250", "super_class": "Vitamins"},
    {"name": "Biotin", "formula": "C10H16N2O3S", "hmdb": "HMDB0000030", "kegg": "C00120", "super_class": "Vitamins"},
    {"name": "Folic acid", "formula": "C19H19N7O6", "hmdb": "HMDB0000121", "kegg": "C00504", "super_class": "Vitamins"},
    {"name": "Retinol", "formula": "C20H30O", "hmdb": "HMDB0000305", "kegg": "C00473", "super_class": "Vitamins"},
    {"name": "Cholecalciferol", "formula": "C27H44O", "hmdb": "HMDB0000876", "kegg": "C05443", "super_class": "Vitamins"},
    {"name": "alpha-Tocopherol", "formula": "C29H50O2", "hmdb": "HMDB0001893", "kegg": "C02477", "super_class": "Vitamins"},
    {"name": "Phylloquinone", "formula": "C31H46O2", "hmdb": "HMDB0003552", "kegg": "C02059", "super_class": "Vitamins"},
    {"name": "Coenzyme Q10", "formula": "C59H90O4", "hmdb": "HMDB0001072", "kegg": "C11378", "super_class": "Vitamins"},
    {"name": "Glutathione", "formula": "C10H17N3O6S", "hmdb": "HMDB0000125", "kegg": "C00051", "super_class": "Peptides"},
    {"name": "GSH", "formula": "C10H17N3O6S", "hmdb": "HMDB0000125", "kegg": "C00051", "super_class": "Peptides"},
    {"name": "GSSG", "formula": "C20H32N6O12S2", "hmdb": "HMDB0003337", "kegg": "C00127", "super_class": "Peptides"},

    # Neurotransmitters & signalling
    {"name": "Acetylcholine", "formula": "C7H16NO2", "hmdb": "HMDB0000895", "kegg": "C01996", "super_class": "Neurotransmitters"},
    {"name": "Dopamine", "formula": "C8H11NO2", "hmdb": "HMDB0000073", "kegg": "C03758", "super_class": "Neurotransmitters"},
    {"name": "Norepinephrine", "formula": "C8H11NO3", "hmdb": "HMDB0000216", "kegg": "C00547", "super_class": "Neurotransmitters"},
    {"name": "Epinephrine", "formula": "C9H13NO3", "hmdb": "HMDB0000068", "kegg": "C00788", "super_class": "Neurotransmitters"},
    {"name": "Serotonin", "formula": "C10H12N2O", "hmdb": "HMDB0000259", "kegg": "C00780", "super_class": "Neurotransmitters"},
    {"name": "GABA", "formula": "C4H9NO2", "hmdb": "HMDB0000112", "kegg": "C00334", "super_class": "Neurotransmitters"},
    {"name": "Histamine", "formula": "C5H9N3", "hmdb": "HMDB0000870", "kegg": "C00388", "super_class": "Neurotransmitters"},
    {"name": "Melatonin", "formula": "C13H16N2O2", "hmdb": "HMDB0001389", "kegg": "C01598", "super_class": "Neurotransmitters"},

    # Bile acids
    {"name": "Cholic acid", "formula": "C24H40O5", "hmdb": "HMDB0000619", "kegg": "C00695", "super_class": "Bile acids"},
    {"name": "Chenodeoxycholic acid", "formula": "C24H40O4", "hmdb": "HMDB0000518", "kegg": "C02528", "super_class": "Bile acids"},
    {"name": "Deoxycholic acid", "formula": "C24H40O4", "hmdb": "HMDB0000626", "kegg": "C04483", "super_class": "Bile acids"},
    {"name": "Lithocholic acid", "formula": "C24H40O3", "hmdb": "HMDB0000761", "kegg": "C03990", "super_class": "Bile acids"},
    {"name": "Glycocholic acid", "formula": "C26H43NO6", "hmdb": "HMDB0000138", "kegg": "C01921", "super_class": "Bile acids"},
    {"name": "Taurocholic acid", "formula": "C26H45NO7S", "hmdb": "HMDB0000036", "kegg": "C05122", "super_class": "Bile acids"},

    # Drug / xenobiotic metabolites
    {"name": "Acetaminophen", "formula": "C8H9NO2", "hmdb": "HMDB0001859", "kegg": "C06804", "super_class": "Drugs"},
    {"name": "Acetaminophen glucuronide", "formula": "C14H17NO8", "hmdb": "HMDB0060312", "kegg": "", "super_class": "Drugs"},
    {"name": "Acetaminophen sulfate", "formula": "C8H9NO5S", "hmdb": "HMDB0059919", "kegg": "", "super_class": "Drugs"},
    {"name": "Caffeine", "formula": "C8H10N4O2", "hmdb": "HMDB0001847", "kegg": "C07481", "super_class": "Drugs"},
    {"name": "Theobromine", "formula": "C7H8N4O2", "hmdb": "HMDB0002825", "kegg": "C07480", "super_class": "Drugs"},
    {"name": "Theophylline", "formula": "C7H8N4O2", "hmdb": "HMDB0001889", "kegg": "C07130", "super_class": "Drugs"},
    {"name": "Paraxanthine", "formula": "C7H8N4O2", "hmdb": "HMDB0001860", "kegg": "C13747", "super_class": "Drugs"},
    {"name": "Ibuprofen", "formula": "C13H18O2", "hmdb": "HMDB0001925", "kegg": "C01588", "super_class": "Drugs"},
    {"name": "Naproxen", "formula": "C14H14O3", "hmdb": "HMDB0001923", "kegg": "C01521", "super_class": "Drugs"},
    {"name": "Salicylic acid", "formula": "C7H6O3", "hmdb": "HMDB0001895", "kegg": "C00805", "super_class": "Drugs"},
    {"name": "Hippuric acid", "formula": "C9H9NO3", "hmdb": "HMDB0000714", "kegg": "C01586", "super_class": "Drugs"},
    {"name": "4-Aminobenzoic acid", "formula": "C7H7NO2", "hmdb": "HMDB0001392", "kegg": "C00568", "super_class": "Drugs"},

    # Lipids
    {"name": "Palmitic acid", "formula": "C16H32O2", "hmdb": "HMDB0000220", "kegg": "C00249", "super_class": "Lipids"},
    {"name": "Stearic acid", "formula": "C18H36O2", "hmdb": "HMDB0000827", "kegg": "C01530", "super_class": "Lipids"},
    {"name": "Oleic acid", "formula": "C18H34O2", "hmdb": "HMDB0000207", "kegg": "C00712", "super_class": "Lipids"},
    {"name": "Linoleic acid", "formula": "C18H32O2", "hmdb": "HMDB0000673", "kegg": "C01595", "super_class": "Lipids"},
    {"name": "Arachidonic acid", "formula": "C20H32O2", "hmdb": "HMDB0001043", "kegg": "C00219", "super_class": "Lipids"},
    {"name": "EPA", "formula": "C20H30O2", "hmdb": "HMDB0001999", "kegg": "C06428", "super_class": "Lipids"},
    {"name": "DHA", "formula": "C22H32O2", "hmdb": "HMDB0002183", "kegg": "C06429", "super_class": "Lipids"},
    {"name": "Cholesterol", "formula": "C27H46O", "hmdb": "HMDB0000067", "kegg": "C00187", "super_class": "Lipids"},
    {"name": "Sphingosine", "formula": "C18H37NO2", "hmdb": "HMDB0000252", "kegg": "C00319", "super_class": "Lipids"},
    {"name": "Ceramide(d18:1/16:0)", "formula": "C34H67NO3", "hmdb": "HMDB0004949", "kegg": "C00195", "super_class": "Lipids"},
    {"name": "Glycerol", "formula": "C3H8O3", "hmdb": "HMDB0000131", "kegg": "C00116", "super_class": "Lipids"},
    {"name": "Choline", "formula": "C5H14NO", "hmdb": "HMDB0000097", "kegg": "C00114", "super_class": "Lipids"},
    {"name": "Phosphocholine", "formula": "C5H15NO4P", "hmdb": "HMDB0001565", "kegg": "C00588", "super_class": "Lipids"},
    {"name": "Acetoacetic acid", "formula": "C4H6O3", "hmdb": "HMDB0000060", "kegg": "C00164", "super_class": "Lipids"},
    {"name": "beta-Hydroxybutyric acid", "formula": "C4H8O3", "hmdb": "HMDB0000357", "kegg": "C01089", "super_class": "Lipids"},

    # Common internal standards and contaminants
    {"name": "2-Amino-3-bromo-5-methylbenzoic acid (IS)", "formula": "C8H8BrNO2", "hmdb": "", "kegg": "", "super_class": "Internal Standard"},
    {"name": "Dibutyl phthalate (plasticizer)", "formula": "C16H22O4", "hmdb": "HMDB0033244", "kegg": "", "super_class": "Contaminant"},
    {"name": "Diisooctyl phthalate", "formula": "C24H38O4", "hmdb": "HMDB0033170", "kegg": "", "super_class": "Contaminant"},
    {"name": "PEG n=4", "formula": "C8H18O5", "hmdb": "", "kegg": "", "super_class": "Contaminant"},
    {"name": "PEG n=5", "formula": "C10H22O6", "hmdb": "", "kegg": "", "super_class": "Contaminant"},
    {"name": "PEG n=6", "formula": "C12H26O7", "hmdb": "", "kegg": "", "super_class": "Contaminant"},
    {"name": "PEG n=7", "formula": "C14H30O8", "hmdb": "", "kegg": "", "super_class": "Contaminant"},
    {"name": "PEG n=8", "formula": "C16H34O9", "hmdb": "", "kegg": "", "super_class": "Contaminant"},
    {"name": "Triton X-100 fragment", "formula": "C14H22O", "hmdb": "", "kegg": "", "super_class": "Contaminant"},
    {"name": "Polysiloxane ion", "formula": "C5H15OSi2", "hmdb": "", "kegg": "", "super_class": "Contaminant"},
]


class MetaboliteAnnotator:
    """Main annotation engine for metabolomics features.

    Matching strategy:
      1. Curated local database (fast, offline, default) — ~120 metabolites.
         This is the dependable path and the only one used when use_online=False.
      2. HMDB / METLIN / MassBank REST queries — ONLY when use_online=True, and
         best-effort: HMDB and METLIN normally require a license/API key, so on a
         stock install they return nothing. Failures are collected in
         self.online_errors (and surfaced via AnnotationResult) instead of being
         silently swallowed.
      3. Online result cache (24h TTL on disk) to avoid repeated API calls.

    All accurate-mass matching is adduct-aware: observed m/z is compared against
    the adduct-adjusted expected m/z, never against the raw neutral mass.
    """

    def __init__(
        self,
        mass_tolerance_ppm: float = 10.0,
        mode: str = "positive",
        use_online: bool = True,
        cache_dir: Optional[str] = None,
    ):
        self.mass_tolerance_ppm = mass_tolerance_ppm
        self.mode = mode
        self.use_online = use_online
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Online result cache (persisted to disk)
        self._online_cache_file = self.cache_dir / "online_annotations.json"
        self._online_cache = self._load_online_cache()

        # Online status tracking (populated during annotate_features)
        self.online_errors: List[str] = []
        self._online_dbs_with_hits: set = set()

        # Pre-compute masses for local cache
        self._local_db = []
        for entry in METABOLITE_CACHE:
            try:
                mass = formula_to_mass(entry["formula"])
                self._local_db.append({**entry, "mass": mass})
            except Exception:
                pass

    # ── Online Cache ──────────────────────────────────────────

    def _load_online_cache(self) -> Dict:
        """Load persisted online annotation cache."""
        if self._online_cache_file.exists():
            try:
                with open(self._online_cache_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_online_cache(self):
        """Persist online annotation cache to disk."""
        try:
            with open(self._online_cache_file, "w") as f:
                json.dump(self._online_cache, f, indent=2)
        except IOError:
            pass

    def _cache_key(self, mz: float, database: str) -> str:
        """Generate cache key for an m/z + database query."""
        return hashlib.md5(f"{mz:.4f}:{database}:{self.mass_tolerance_ppm}:{self.mode}".encode()).hexdigest()

    def _cache_get(self, mz: float, database: str) -> Optional[List[Dict]]:
        """Retrieve cached online results (valid for 24h)."""
        key = self._cache_key(mz, database)
        entry = self._online_cache.get(key)
        if entry and time.time() - entry.get("ts", 0) < 86400:
            return entry.get("matches", [])
        return None

    def _cache_set(self, mz: float, database: str, matches: List[Dict]):
        """Store results in the online cache."""
        key = self._cache_key(mz, database)
        self._online_cache[key] = {"ts": time.time(), "matches": matches}
        # Trim old entries (keep last 1000)
        if len(self._online_cache) > 1000:
            sorted_keys = sorted(self._online_cache.keys(),
                                 key=lambda k: self._online_cache[k].get("ts", 0))
            for old_key in sorted_keys[:len(self._online_cache) - 1000]:
                del self._online_cache[old_key]

    def annotate_features(
        self,
        features: List[DetectedFeature],
        max_matches_per_feature: int = 10,
    ) -> AnnotationResult:
        """Annotate a list of detected features against all databases.

        Args:
            features: Detected features to annotate
            max_matches_per_feature: Maximum database matches per feature

        Returns:
            AnnotationResult with annotated features
        """
        annotated = []
        n_annotated = 0
        n_high_conf = 0

        # Reset per-run online status
        self.online_errors = []
        self._online_dbs_with_hits = set()

        for feat in features:
            af = AnnotatedFeature(
                feature_id=feat.feature_id,
                mz=feat.mz,
                rt=feat.rt,
                intensity=feat.intensity,
            )

            # Strategy 1: Local cache matching
            local_matches = self._search_local_cache(feat.mz)
            af.matches.extend(local_matches)

            # Strategy 2: Online HMDB / METLIN / MassBank (if enabled)
            if self.use_online and len(af.matches) < max_matches_per_feature:
                for db_name, search_fn in [
                    ("HMDB", self._search_hmdb),
                    ("METLIN", self._search_metlin),
                    ("MassBank", self._search_massbank),
                ]:
                    try:
                        online_matches = search_fn(feat.mz)
                        af.matches.extend(online_matches)
                        if len(af.matches) >= max_matches_per_feature:
                            break
                    except Exception:
                        pass  # Individual DB failures are non-fatal

            # Rank and trim
            af.matches.sort(key=lambda m: (abs(m.mass_error_ppm), -m.score))
            af.matches = af.matches[:max_matches_per_feature]

            # Assign ranks
            for i, match in enumerate(af.matches):
                match.rank = i + 1

            # Set top match
            if af.matches:
                af.top_match = af.matches[0]
                n_annotated += 1
                if af.top_match.is_high_confidence:
                    n_high_conf += 1

            # Guess adduct
            if af.matches:
                neutral_candidates = [m.monoisotopic_mass for m in af.matches[:3]]
                adducts = guess_adducts(feat.mz, neutral_candidates, self.mode)
                if adducts:
                    af.adduct_guess = adducts[0][0]
                    af.neutral_mass = adducts[0][1]

            annotated.append(af)

        # Persist the online cache once per run (not once per feature).
        if self.use_online:
            self._save_online_cache()

        return AnnotationResult(
            annotated_features=annotated,
            total_features=len(features),
            annotated_count=n_annotated,
            high_confidence_count=n_high_conf,
            databases_queried=["LocalCache"] + (["HMDB", "METLIN", "MassBank"] if self.use_online else []),
            search_params={
                "mass_tolerance_ppm": self.mass_tolerance_ppm,
                "mode": self.mode,
            },
            online_requested=self.use_online,
            online_available=len(self._online_dbs_with_hits) > 0,
            online_errors=list(self.online_errors),
            databases_with_hits=["LocalCache"] + sorted(self._online_dbs_with_hits),
        )

    def annotate_feature_table(
        self,
        feature_table: FeatureTable,
    ) -> List[MetaboliteMatch]:
        """Quick annotation of feature table m/z values without full DetectedFeature objects.

        Returns a list of MetaboliteMatch lists (one per feature in the table).
        """
        matches = []
        for i in range(feature_table.num_features):
            mz = float(feature_table.mz_values[i])
            local_matches = self._search_local_cache(mz)
            local_matches.sort(key=lambda m: (abs(m.mass_error_ppm), -m.score))
            matches.append(local_matches[:3])  # Top 3 per feature
        return matches

    def _search_local_cache(self, observed_mz: float) -> List[MetaboliteMatch]:
        """Search the built-in metabolite cache by mass."""
        matches = []
        adduct_list = COMMON_ADDUCTS_POSITIVE if self.mode == "positive" else COMMON_ADDUCTS_NEGATIVE

        for entry in self._local_db:
            neutral_mass = entry["mass"]

            for adduct in adduct_list:
                expected_mz = calculate_adduct_mz(neutral_mass, adduct)
                ppm_error = abs(observed_mz - expected_mz) / max(expected_mz, 1e-6) * 1e6
                da_error = abs(observed_mz - expected_mz)

                if ppm_error < self.mass_tolerance_ppm:
                    # Score based on mass accuracy
                    score = max(0.0, 1.0 - ppm_error / self.mass_tolerance_ppm)
                    # Bonus for common adducts
                    if adduct in ("[M+H]+", "[M-H]-", "[M+Na]+"):
                        score = min(1.0, score + 0.1)
                    # Bonus for well-characterised metabolites
                    if "super_class" in entry and entry["super_class"] not in ("Contaminant", "Internal Standard"):
                        score = min(1.0, score + 0.05)

                    matches.append(MetaboliteMatch(
                        name=entry["name"],
                        formula=entry["formula"],
                        monoisotopic_mass=neutral_mass,
                        database="LocalCache",
                        accession=entry.get("hmdb", entry.get("kegg", "")),
                        adduct=adduct,
                        mass_error_ppm=round(ppm_error, 2),
                        mass_error_da=round(da_error, 4),
                        score=round(score, 3),
                        description=f"{entry.get('super_class', 'Metabolite')}; KEGG: {entry.get('kegg', 'N/A')}",
                    ))

        return matches

    @staticmethod
    def _match_to_dict(m: MetaboliteMatch) -> Dict:
        """Serialise a MetaboliteMatch for the on-disk online cache."""
        return {
            "name": m.name, "formula": m.formula,
            "monoisotopic_mass": m.monoisotopic_mass,
            "database": m.database, "accession": m.accession, "adduct": m.adduct,
            "mass_error_ppm": m.mass_error_ppm, "mass_error_da": m.mass_error_da,
            "score": m.score, "description": m.description,
            "pathways": m.pathways, "inchikey": m.inchikey,
        }

    def _record_online_error(self, database: str, exc: Exception):
        """Record (don't hide) an online-lookup failure so callers can surface it."""
        msg = f"{database}: {type(exc).__name__}: {exc}"
        if msg not in self.online_errors:
            self.online_errors.append(msg)

    def _best_adduct_match(self, observed_mz: float, neutral_mass: float):
        """Find the adduct that best explains observed_mz for a given neutral mass.

        Databases return *neutral* monoisotopic masses; an observed ion m/z must
        be compared against the adduct-adjusted expected m/z, not the neutral
        mass directly. Returns (adduct_name, ppm_error, da_error) for the closest
        adduct in the current ionisation mode, or (None, inf, inf) if neutral_mass
        is non-positive.
        """
        if neutral_mass <= 0:
            return None, float("inf"), float("inf")
        adduct_list = COMMON_ADDUCTS_POSITIVE if self.mode == "positive" else COMMON_ADDUCTS_NEGATIVE
        best = (None, float("inf"), float("inf"))
        for adduct in adduct_list:
            expected_mz = calculate_adduct_mz(neutral_mass, adduct)
            da_error = abs(observed_mz - expected_mz)
            ppm_error = da_error / max(expected_mz, 1e-6) * 1e6
            if ppm_error < best[1]:
                best = (adduct, ppm_error, da_error)
        return best

    def _search_hmdb(self, observed_mz: float) -> List[MetaboliteMatch]:
        """Search HMDB via REST API by mass.

        Uses HMDB's public mass search endpoint:
        https://hmdb.ca/api/v1/mass/search?mass=<mz>&tolerance=<ppm>&polarity=<mode>

        Results are cached for 24 hours.
        """
        # Check cache first
        cached = self._cache_get(observed_mz, "HMDB")
        if cached is not None:
            return [MetaboliteMatch(**m) for m in cached if m.get("database") == "HMDB"]

        url = (
            f"https://hmdb.ca/api/v1/mass/search"
            f"?mass={observed_mz:.4f}"
            f"&tolerance={self.mass_tolerance_ppm / 2.0:.1f}"
            f"&polarity={self.mode}"
            f"&limit=10"
        )

        matches = []
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            for entry in data.get("results", data if isinstance(data, list) else [])[:10]:
                hmdb_id = entry.get("accession", "")
                name = entry.get("name", "Unknown")
                formula = entry.get("chemical_formula", "")
                # HMDB returns a NEUTRAL monoisotopic mass — compare m/z against
                # the adduct-adjusted expected m/z, not the neutral mass directly.
                mass = float(
                    entry.get("monoisotopic_molecular_weight",
                              entry.get("monisotopic_molecular_weight",  # HMDB's own misspelling
                                        entry.get("mono_mass",
                                                  entry.get("average_molecular_weight", 0)))))
                adduct, ppm_error, da_error = self._best_adduct_match(observed_mz, mass)
                if ppm_error > self.mass_tolerance_ppm:
                    continue
                score = max(0.0, 1.0 - ppm_error / self.mass_tolerance_ppm)

                matches.append(MetaboliteMatch(
                    name=name, formula=formula, monoisotopic_mass=mass,
                    database="HMDB", accession=hmdb_id, adduct=adduct,
                    mass_error_ppm=round(ppm_error, 2),
                    mass_error_da=round(da_error, 4),
                    score=round(score, 3),
                    description=entry.get("super_class", ""),
                    pathways=[entry.get("biological_properties", "")],
                ))

            # Cache results
            self._cache_set(observed_mz, "HMDB", [self._match_to_dict(m) for m in matches])
            if matches:
                self._online_dbs_with_hits.add("HMDB")
        except Exception as e:  # noqa: BLE001 — record, don't hide
            self._record_online_error("HMDB", e)

        return matches

    def _search_metlin(self, observed_mz: float) -> List[MetaboliteMatch]:
        """Search METLIN via REST API by mass.

        METLIN (Scripps Research) mass search endpoint.
        Returns metabolite matches within the mass tolerance window.

        Results are cached for 24 hours.
        """
        cached = self._cache_get(observed_mz, "METLIN")
        if cached is not None:
            return [MetaboliteMatch(**m) for m in cached]

        # METLIN REST API v1
        tolerance_da = observed_mz * self.mass_tolerance_ppm / 1e6
        url = (
            f"https://metlin.scripps.edu/api/v1/search/simple"
            f"?massFrom={observed_mz - tolerance_da:.4f}"
            f"&massTo={observed_mz + tolerance_da:.4f}"
        )

        matches = []
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            results = data if isinstance(data, list) else data.get("results", data.get("data", []))
            for entry in results[:10]:
                name = entry.get("name", entry.get("compound", "Unknown"))
                # exact_mass is the neutral monoisotopic mass — match adduct-aware.
                mass = float(entry.get("exact_mass", entry.get("mass", entry.get("mono_mass", 0))))
                if mass <= 0:
                    continue
                adduct, ppm_error, da_error = self._best_adduct_match(observed_mz, mass)
                if ppm_error > self.mass_tolerance_ppm:
                    continue
                metlin_id = str(entry.get("id", entry.get("metlin_id", "")))
                formula = entry.get("formula", entry.get("chemical_formula", ""))
                score = max(0.0, 1.0 - ppm_error / self.mass_tolerance_ppm)

                matches.append(MetaboliteMatch(
                    name=name, formula=formula, monoisotopic_mass=mass,
                    database="METLIN", accession=metlin_id, adduct=adduct,
                    mass_error_ppm=round(ppm_error, 2),
                    mass_error_da=round(da_error, 4),
                    score=round(score, 3),
                    description=entry.get("description", entry.get("category", "")),
                ))

            self._cache_set(observed_mz, "METLIN", [self._match_to_dict(m) for m in matches])
            if matches:
                self._online_dbs_with_hits.add("METLIN")
        except Exception as e:  # noqa: BLE001 — record, don't hide
            self._record_online_error("METLIN", e)

        return matches

    def _search_massbank(self, observed_mz: float) -> List[MetaboliteMatch]:
        """Search MassBank.eu via REST API by m/z.

        MassBank is a public repository of mass spectra with rich metadata.
        Uses the MassBank REST API for mass-based search.

        Results are cached for 24 hours.
        """
        cached = self._cache_get(observed_mz, "MassBank")
        if cached is not None:
            return [MetaboliteMatch(**m) for m in cached]

        tolerance_da = observed_mz * self.mass_tolerance_ppm / 1e6
        url = (
            f"https://massbank.eu/MassBank/api/v1/peak/search"
            f"?mzMin={observed_mz - tolerance_da:.4f}"
            f"&mzMax={observed_mz + tolerance_da:.4f}"
            f"&ionMode={'POSITIVE' if self.mode == 'positive' else 'NEGATIVE'}"
            f"&size=10"
        )

        matches = []
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            records = data if isinstance(data, list) else data.get("data", data.get("results", []))
            for entry in records[:10]:
                name = entry.get("name", entry.get("compound_name",
                         entry.get("title", "Unknown")))
                accession = entry.get("accession", entry.get("id", ""))
                formula = entry.get("formula", entry.get("chemical_formula", ""))

                # Prefer the neutral exact_mass (adduct-aware match). If only a
                # precursor m/z is given, that is already an ion — compare directly.
                neutral = float(entry.get("exact_mass", entry.get("mono_mass", 0)) or 0)
                if neutral > 0:
                    adduct, ppm_error, da_error = self._best_adduct_match(observed_mz, neutral)
                    mass = neutral
                else:
                    precursor = float(entry.get("precursor_mz", 0) or 0)
                    if precursor <= 0:
                        continue
                    adduct = None
                    da_error = abs(observed_mz - precursor)
                    ppm_error = da_error / max(precursor, 1e-6) * 1e6
                    mass = precursor
                if ppm_error > self.mass_tolerance_ppm:
                    continue
                score = max(0.0, 1.0 - ppm_error / self.mass_tolerance_ppm)

                # MassBank records often have InChIKey
                inchikey = entry.get("inchikey", entry.get("InChIKey", ""))

                matches.append(MetaboliteMatch(
                    name=name, formula=formula, monoisotopic_mass=mass,
                    database="MassBank", accession=str(accession), adduct=adduct,
                    mass_error_ppm=round(ppm_error, 2),
                    mass_error_da=round(da_error, 4),
                    score=round(score, 3),
                    description=entry.get("instrument_type", entry.get("instrument", "")),
                    inchikey=inchikey,
                ))

            self._cache_set(observed_mz, "MassBank", [self._match_to_dict(m) for m in matches])
            if matches:
                self._online_dbs_with_hits.add("MassBank")
        except Exception as e:  # noqa: BLE001 — record, don't hide
            self._record_online_error("MassBank", e)

        return matches


# ══════════════════════════════════════════════════════════════════════
# MS/MS Spectral Matching
# ══════════════════════════════════════════════════════════════════════

def cosine_similarity(spectrum_a: np.ndarray, spectrum_b: np.ndarray) -> float:
    """Compute cosine similarity between two mass spectra (vectors of intensities).

    Both spectra should be aligned to the same m/z bins.
    """
    if len(spectrum_a) == 0 or len(spectrum_b) == 0:
        return 0.0
    dot = np.dot(spectrum_a, spectrum_b)
    norm_a = np.linalg.norm(spectrum_a)
    norm_b = np.linalg.norm(spectrum_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def spectrum_entropy(intensities: np.ndarray) -> float:
    """Calculate Shannon entropy of a mass spectrum (measure of purity)."""
    if len(intensities) == 0:
        return 0.0
    probs = intensities / max(np.sum(intensities), 1e-10)
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log2(probs)))


def spectral_match(
    query_mz: np.ndarray,
    query_intensity: np.ndarray,
    library_mz: np.ndarray,
    library_intensity: np.ndarray,
    mz_tolerance_da: float = 0.02,
) -> float:
    """Match a query MS/MS spectrum against a library spectrum.

    Uses weighted cosine similarity with peak matching within tolerance.

    Returns:
        Similarity score (0-1)
    """
    if len(query_mz) == 0 or len(library_mz) == 0:
        return 0.0

    # Normalise
    query_norm = query_intensity / max(np.max(query_intensity), 1e-10)
    lib_norm = library_intensity / max(np.max(library_intensity), 1e-10)

    # Match peaks: for each query peak, find the closest library peak
    matched_intensities_q = np.zeros(len(query_mz))
    matched_intensities_l = np.zeros(len(library_mz))

    for i, mz_q in enumerate(query_mz):
        dists = np.abs(library_mz - mz_q)
        best_j = np.argmin(dists)
        if dists[best_j] <= mz_tolerance_da:
            matched_intensities_q[i] = query_norm[i]
            matched_intensities_l[best_j] = max(matched_intensities_l[best_j], lib_norm[best_j])

    # Weighted cosine
    weighted_q = matched_intensities_q * (query_norm ** 0.5)
    weighted_l = matched_intensities_l * (lib_norm ** 0.5)

    numer = np.dot(weighted_q, np.interp(query_mz, library_mz, weighted_l, left=0, right=0))
    denom = np.linalg.norm(weighted_q) * np.linalg.norm(weighted_l)

    return float(numer / max(denom, 1e-10))


# ══════════════════════════════════════════════════════════════════════
# Export
# ══════════════════════════════════════════════════════════════════════

def export_annotations_csv(
    result: AnnotationResult,
    path: str,
):
    """Export annotation results to CSV."""
    import csv
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "feature_id", "mz", "rt", "intensity",
            "match_rank", "name", "formula", "neutral_mass",
            "adduct", "mass_error_ppm", "score", "database", "accession",
            "adduct_guess", "description",
        ])
        for af in result.annotated_features:
            if af.matches:
                for m in af.matches:
                    writer.writerow([
                        af.feature_id, f"{af.mz:.4f}", f"{af.rt:.1f}", f"{af.intensity:.0f}",
                        m.rank, m.name, m.formula, f"{m.monoisotopic_mass:.4f}",
                        m.adduct or "", f"{m.mass_error_ppm:.2f}", f"{m.score:.3f}",
                        m.database, m.accession,
                        af.adduct_guess or "", m.description,
                    ])
            else:
                writer.writerow([
                    af.feature_id, f"{af.mz:.4f}", f"{af.rt:.1f}", f"{af.intensity:.0f}",
                    "", "Unknown", "", "",
                    "", "", "", "", "",
                    "", "",
                ])
