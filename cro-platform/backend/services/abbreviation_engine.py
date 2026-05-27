"""
Biopharma Abbreviation Engine
Auto-expands abbreviations with biopharma context for search scoping.
Prevents irrelevant results when searching industry abbreviations.
"""

# Biopharma abbreviation glossary with expansion + disambiguation context
BIOPHARMA_ABBREVIATIONS = {
    # Preclinical / DMPK
    "DMPK": {
        "full": "Drug Metabolism and Pharmacokinetics",
        "scope": ["drug metabolism", "pharmacokinetics", "PK/PD", "ADME", "preclinical"],
        "exclude": [],
    },
    "ADME": {
        "full": "Absorption Distribution Metabolism Excretion",
        "scope": ["drug absorption", "bioavailability", "metabolic stability", "CYP inhibition"],
        "exclude": [],
    },
    "PK": {
        "full": "Pharmacokinetics",
        "scope": ["drug pharmacokinetics", "PK parameters", "clearance", "volume of distribution", "half-life"],
        "exclude": ["protein kinase"],
    },
    "PD": {
        "full": "Pharmacodynamics",
        "scope": ["drug pharmacodynamics", "efficacy", "biomarker", "target engagement"],
        "exclude": ["Parkinson disease"],
    },
    "TK": {
        "full": "Toxicokinetics",
        "scope": ["toxicokinetics", "GLP tox", "safety assessment", "systemic exposure"],
        "exclude": [],
    },
    "DDI": {
        "full": "Drug-Drug Interaction",
        "scope": ["drug interaction", "CYP inhibition", "transporter", "DDI liability"],
        "exclude": [],
    },

    # Therapeutic modalities
    "ADC": {
        "full": "Antibody-Drug Conjugate",
        "scope": ["antibody drug conjugate", "linker payload", "DAR", "site-specific conjugation", "bystander killing"],
        "exclude": ["analog digital converter"],
    },
    "mAb": {
        "full": "Monoclonal Antibody",
        "scope": ["monoclonal antibody", "therapeutic antibody", "immunoglobulin", "IgG"],
        "exclude": [],
    },
    "PROTAC": {
        "full": "Proteolysis Targeting Chimera",
        "scope": ["targeted protein degradation", "E3 ligase", "ubiquitin proteasome", "heterobifunctional"],
        "exclude": [],
    },
    "siRNA": {
        "full": "Small Interfering RNA",
        "scope": ["RNA interference", "gene silencing", "oligonucleotide therapeutic", "lipid nanoparticle"],
        "exclude": [],
    },
    "ASO": {
        "full": "Antisense Oligonucleotide",
        "scope": ["antisense therapy", "oligonucleotide", "RNase H", "splice modulation"],
        "exclude": [],
    },

    # Development / Regulatory
    "IND": {
        "full": "Investigational New Drug",
        "scope": ["IND application", "FDA", "clinical trial authorization", "pre-IND meeting"],
        "exclude": [],
    },
    "NDA": {
        "full": "New Drug Application",
        "scope": ["FDA approval", "drug registration", "marketing authorization"],
        "exclude": ["non-disclosure agreement"],
    },
    "BLA": {
        "full": "Biologics License Application",
        "scope": ["biologic approval", "FDA biologics", "therapeutic protein", "biosimilar"],
        "exclude": [],
    },
    "CMC": {
        "full": "Chemistry Manufacturing and Controls",
        "scope": ["drug manufacturing", "process development", "quality control", "formulation", "GMP"],
        "exclude": [],
    },
    "CTD": {
        "full": "Common Technical Document",
        "scope": ["regulatory submission", "eCTD", "ICH M4", "drug registration dossier"],
        "exclude": [],
    },
    "GxP": {
        "full": "Good Practice quality guidelines",
        "scope": ["GLP", "GCP", "GMP", "quality assurance", "compliance", "regulatory"],
        "exclude": [],
    },
    "GLP": {
        "full": "Good Laboratory Practice",
        "scope": ["GLP compliance", "safety studies", "FDA GLP", "OECD GLP", "quality system"],
        "exclude": [],
    },
    "GCP": {
        "full": "Good Clinical Practice",
        "scope": ["clinical trial quality", "ICH E6", "trial conduct", "patient safety"],
        "exclude": [],
    },

    # Bioanalytical / Technologies
    "LC-MS": {
        "full": "Liquid Chromatography Mass Spectrometry",
        "scope": ["bioanalysis", "quantification", "proteomics", "MRM", "peptide", "small molecule"],
        "exclude": [],
    },
    "MRM": {
        "full": "Multiple Reaction Monitoring",
        "scope": ["targeted proteomics", "triple quadrupole", "quantification", "surrogate peptide", "LC-MS/MS"],
        "exclude": [],
    },
    "ELISA": {
        "full": "Enzyme-Linked Immunosorbent Assay",
        "scope": ["immunoassay", "ligand binding assay", "ADA", "immunogenicity", "biomarker"],
        "exclude": [],
    },
    "ADA": {
        "full": "Anti-Drug Antibody",
        "scope": ["immunogenicity", "neutralizing antibody", "therapeutic protein", "biosimilar"],
        "exclude": ["Americans with Disabilities Act"],
    },
    "LBA": {
        "full": "Ligand Binding Assay",
        "scope": ["immunoassay", "ELISA", "MSD", "Gyrolab", "protein quantification", "PK assay"],
        "exclude": [],
    },
    "SPR": {
        "full": "Surface Plasmon Resonance",
        "scope": ["Biacore", "binding kinetics", "affinity", "KD", "protein interaction"],
        "exclude": [],
    },

    # CRO / Outsourcing
    "CRO": {
        "full": "Contract Research Organization",
        "scope": ["preclinical CRO", "drug development outsourcing", "contract lab", "bioanalytical CRO"],
        "exclude": [],
    },
    "CDMO": {
        "full": "Contract Development and Manufacturing Organization",
        "scope": ["drug manufacturing outsourcing", "CMC development", "GMP manufacturing"],
        "exclude": [],
    },
    "BD": {
        "full": "Business Development",
        "scope": ["partnership", "licensing", "deal", "strategic alliance", "collaboration"],
        "exclude": [],
    },

    # Disease areas (for therapeutic context)
    "CNS": {
        "full": "Central Nervous System",
        "scope": ["neurological", "Alzheimer", "Parkinson", "brain", "neurodegenerative"],
        "exclude": [],
    },
    "NASH": {
        "full": "Nonalcoholic Steatohepatitis",
        "scope": ["MASH", "fatty liver", "liver fibrosis", "metabolic disease", "hepatic"],
        "exclude": [],
    },
    "CKD": {
        "full": "Chronic Kidney Disease",
        "scope": ["renal disease", "kidney", "nephrology", "glomerular filtration"],
        "exclude": [],
    },
}


def expand_search(query: str) -> dict:
    """
    Expand a search query by detecting biopharma abbreviations and adding
    disambiguation context. Returns the enriched query + explanation.
    """
    words = query.strip().split()
    expansions = []
    excludes = []
    expanded_terms = []
    original_terms = set(words)

    for word in words:
        # Check exact match (case-insensitive)
        upper = word.upper().rstrip(',.;')
        if upper in BIOPHARMA_ABBREVIATIONS:
            abbr = BIOPHARMA_ABBREVIATIONS[upper]
            expansions.append({
                "abbreviation": upper,
                "meaning": abbr["full"],
                "context_added": abbr["scope"][:3],
            })
            expanded_terms.extend(abbr["scope"][:3])
            if abbr["exclude"]:
                excludes.extend(abbr["exclude"])

    if not expansions:
        return {
            "original": query,
            "expanded_query": query,
            "expansions": [],
            "excludes": [],
            "note": "No biopharma abbreviations detected",
        }

    # Build expanded query: original terms + biopharma scope context
    expanded_query = query + " " + " ".join(expanded_terms)

    # Build exclude terms (for when abbreviation has non-biopharma meanings)
    exclude_query = " ".join([f"-{e}" for e in excludes]) if excludes else ""

    return {
        "original": query,
        "expanded_query": expanded_query.strip(),
        "exclude_query": exclude_query,
        "expansions": expansions,
        "excludes": excludes,
        "note": f"Auto-scoped to biopharma: {', '.join(e['meaning'] for e in expansions[:3])}",
    }


def get_abbreviation_meaning(abbr: str) -> dict:
    """Look up a single abbreviation."""
    upper = abbr.upper().strip()
    if upper in BIOPHARMA_ABBREVIATIONS:
        return {"found": True, **BIOPHARMA_ABBREVIATIONS[upper]}
    return {"found": False, "suggestion": "Not a known biopharma abbreviation"}


def list_abbreviations(category: str = None) -> list:
    """List all known biopharma abbreviations, optionally filtered by category."""
    categories = {
        "dmpk": ["DMPK", "ADME", "PK", "PD", "TK", "DDI"],
        "modality": ["ADC", "mAb", "PROTAC", "siRNA", "ASO"],
        "regulatory": ["IND", "NDA", "BLA", "CMC", "CTD", "GxP", "GLP", "GCP"],
        "bioanalytical": ["LC-MS", "MRM", "ELISA", "ADA", "LBA", "SPR"],
        "business": ["CRO", "CDMO", "BD"],
        "disease": ["CNS", "NASH", "CKD"],
    }

    if category and category.lower() in categories:
        keys = categories[category.lower()]
    else:
        keys = BIOPHARMA_ABBREVIATIONS.keys()

    return [
        {"abbreviation": k, "meaning": BIOPHARMA_ABBREVIATIONS[k]["full"]}
        for k in sorted(keys)
    ]
