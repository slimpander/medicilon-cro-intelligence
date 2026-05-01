#!/usr/bin/env python3
"""
CRO Competitive Intelligence Scraper
Visits CRO websites and extracts service + location data.
Falls back to curated data if scraping fails (many CRO sites are JS-heavy).

Usage:
    pip install requests beautifulsoup4
    python scraper.py
Output: data/cro_data.json
"""

import json
import os
import time
import re
from datetime import date
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False
    print("WARNING: requests/beautifulsoup4 not installed. Using curated data only.")
    print("Install with: pip install requests beautifulsoup4")

# ─── Curated Fallback Data ────────────────────────────────────────────────────

CURATED_DATA = {
    "metadata": {
        "generated": str(date.today()),
        "source": "curated",
        "version": "1.0"
    },
    "service_categories": [
        "In Vivo / Mouse Services",
        "DMPK",
        "ADME",
        "Toxicology",
        "Bioanalysis",
        "CMC",
        "Clinical Trials",
        "Regulatory Affairs",
        "Biomarker / Genomics",
        "Protein Sciences / Biologics"
    ],
    "cros": [
        {
            "id": "charles_river",
            "name": "Charles River Laboratories",
            "short_name": "Charles River",
            "website": "charlesriver.com",
            "is_medicilon": False,
            "states": ["MA", "NJ", "NC", "PA", "TX", "CA", "WA", "MI", "OH", "NY"],
            "cities": [
                {"city": "Wilmington", "state": "MA"},
                {"city": "Skokie", "state": "IL"},
                {"city": "Raleigh", "state": "NC"},
                {"city": "Horsham", "state": "PA"},
                {"city": "Houston", "state": "TX"},
                {"city": "Hollister", "state": "CA"},
                {"city": "Redmond", "state": "WA"},
                {"city": "Ann Arbor", "state": "MI"},
                {"city": "Cincinnati", "state": "OH"},
                {"city": "Saugerties", "state": "NY"}
            ],
            "services": [
                "In Vivo / Mouse Services",
                "DMPK",
                "ADME",
                "Toxicology",
                "Bioanalysis",
                "CMC",
                "Regulatory Affairs"
            ],
            "description": "Leading global CRO offering comprehensive early and late-stage drug development services.",
            "tier": 1
        },
        {
            "id": "covance",
            "name": "Covance / Labcorp Drug Development",
            "short_name": "Covance / Labcorp",
            "website": "labcorp.com/drug-development",
            "is_medicilon": False,
            "states": ["WI", "NJ", "IN", "TX", "VA", "NC", "CA", "CO"],
            "cities": [
                {"city": "Madison", "state": "WI"},
                {"city": "Princeton", "state": "NJ"},
                {"city": "Indianapolis", "state": "IN"},
                {"city": "Austin", "state": "TX"},
                {"city": "Vienna", "state": "VA"},
                {"city": "Durham", "state": "NC"},
                {"city": "San Diego", "state": "CA"},
                {"city": "Denver", "state": "CO"}
            ],
            "services": [
                "DMPK",
                "ADME",
                "Toxicology",
                "Bioanalysis",
                "CMC",
                "Clinical Trials",
                "Regulatory Affairs",
                "Biomarker / Genomics"
            ],
            "description": "Full-service CRO with global reach from early discovery to post-market surveillance.",
            "tier": 1
        },
        {
            "id": "wuxi",
            "name": "WuXi AppTec",
            "short_name": "WuXi AppTec",
            "website": "wuxiapptec.com",
            "is_medicilon": False,
            "states": ["NJ", "PA", "GA", "MN", "CA", "TX"],
            "cities": [
                {"city": "Plainsboro", "state": "NJ"},
                {"city": "Philadelphia", "state": "PA"},
                {"city": "Atlanta", "state": "GA"},
                {"city": "St. Paul", "state": "MN"},
                {"city": "San Diego", "state": "CA"},
                {"city": "Houston", "state": "TX"}
            ],
            "services": [
                "DMPK",
                "ADME",
                "Toxicology",
                "Bioanalysis",
                "CMC",
                "Protein Sciences / Biologics"
            ],
            "description": "Global open-access platform offering integrated drug R&D and manufacturing.",
            "tier": 1
        },
        {
            "id": "eurofins",
            "name": "Eurofins Scientific",
            "short_name": "Eurofins",
            "website": "eurofins.com",
            "is_medicilon": False,
            "states": ["CA", "PA", "TX", "NJ", "NC", "MO", "WI", "IL"],
            "cities": [
                {"city": "San Diego", "state": "CA"},
                {"city": "Lancaster", "state": "PA"},
                {"city": "Austin", "state": "TX"},
                {"city": "Piscataway", "state": "NJ"},
                {"city": "Research Triangle Park", "state": "NC"},
                {"city": "St. Louis", "state": "MO"},
                {"city": "Milwaukee", "state": "WI"},
                {"city": "Chicago", "state": "IL"}
            ],
            "services": [
                "Bioanalysis",
                "Toxicology",
                "ADME",
                "DMPK",
                "CMC",
                "Biomarker / Genomics"
            ],
            "description": "Multinational testing lab network with broad analytical and bioanalytical capabilities.",
            "tier": 1
        },
        {
            "id": "pharmaron",
            "name": "Pharmaron",
            "short_name": "Pharmaron",
            "website": "pharmaron.com",
            "is_medicilon": False,
            "states": ["KY", "CA", "MD"],
            "cities": [
                {"city": "Lexington", "state": "KY"},
                {"city": "San Diego", "state": "CA"},
                {"city": "Baltimore", "state": "MD"}
            ],
            "services": [
                "DMPK",
                "ADME",
                "Toxicology",
                "Bioanalysis",
                "CMC"
            ],
            "description": "Integrated pharmaceutical R&D services with strong China-US footprint.",
            "tier": 2
        },
        {
            "id": "crown_bio",
            "name": "Crown Bioscience",
            "short_name": "Crown Bioscience",
            "website": "crownbio.com",
            "is_medicilon": False,
            "states": ["CA", "NJ", "TX"],
            "cities": [
                {"city": "San Diego", "state": "CA"},
                {"city": "Cranbury", "state": "NJ"},
                {"city": "Houston", "state": "TX"}
            ],
            "services": [
                "In Vivo / Mouse Services",
                "Biomarker / Genomics",
                "Protein Sciences / Biologics"
            ],
            "description": "Oncology and metabolic disease-focused CRO specializing in translational models.",
            "tier": 2
        },
        {
            "id": "syneos",
            "name": "Syneos Health",
            "short_name": "Syneos Health",
            "website": "syneoshealth.com",
            "is_medicilon": False,
            "states": ["NC", "NJ", "CA", "TX", "PA", "FL", "NY"],
            "cities": [
                {"city": "Morrisville", "state": "NC"},
                {"city": "Bridgewater", "state": "NJ"},
                {"city": "San Francisco", "state": "CA"},
                {"city": "Dallas", "state": "TX"},
                {"city": "Philadelphia", "state": "PA"},
                {"city": "Miami", "state": "FL"},
                {"city": "New York", "state": "NY"}
            ],
            "services": [
                "Clinical Trials",
                "Regulatory Affairs",
                "Biomarker / Genomics"
            ],
            "description": "Biopharmaceutical solutions company specializing in clinical development and commercialization.",
            "tier": 1
        },
        {
            "id": "icon",
            "name": "ICON plc",
            "short_name": "ICON plc",
            "website": "iconplc.com",
            "is_medicilon": False,
            "states": ["CA", "TX", "NJ", "NC", "PA", "MN", "FL", "NY"],
            "cities": [
                {"city": "San Francisco", "state": "CA"},
                {"city": "San Antonio", "state": "TX"},
                {"city": "Blue Bell", "state": "PA"},
                {"city": "Durham", "state": "NC"},
                {"city": "Minneapolis", "state": "MN"},
                {"city": "Tampa", "state": "FL"},
                {"city": "New York", "state": "NY"}
            ],
            "services": [
                "Clinical Trials",
                "Regulatory Affairs",
                "Bioanalysis",
                "DMPK"
            ],
            "description": "Global CRO supporting clinical development including PRA Health Sciences capabilities.",
            "tier": 1
        },
        {
            "id": "bioagilytix",
            "name": "BioAgilytix",
            "short_name": "BioAgilytix",
            "website": "bioagilytix.com",
            "is_medicilon": False,
            "states": ["NC", "TX", "MA"],
            "cities": [
                {"city": "Durham", "state": "NC"},
                {"city": "San Antonio", "state": "TX"},
                {"city": "Boston", "state": "MA"}
            ],
            "services": [
                "Bioanalysis",
                "Biomarker / Genomics",
                "Protein Sciences / Biologics"
            ],
            "description": "Large molecule bioanalysis specialist with immunoassay and cell-based assay expertise.",
            "tier": 2
        },
        {
            "id": "altasciences",
            "name": "Altasciences",
            "short_name": "Altasciences",
            "website": "altasciences.com",
            "is_medicilon": False,
            "states": ["WA", "CA", "KS", "MO"],
            "cities": [
                {"city": "Everett", "state": "WA"},
                {"city": "San Diego", "state": "CA"},
                {"city": "Lenexa", "state": "KS"},
                {"city": "Kansas City", "state": "MO"}
            ],
            "services": [
                "DMPK",
                "ADME",
                "Toxicology",
                "Bioanalysis",
                "Clinical Trials"
            ],
            "description": "Integrated early phase CRO offering preclinical and Phase I services.",
            "tier": 2
        },
        {
            "id": "celerion",
            "name": "Celerion",
            "short_name": "Celerion",
            "website": "celerion.com",
            "is_medicilon": False,
            "states": ["NE", "AZ", "NV", "OR"],
            "cities": [
                {"city": "Lincoln", "state": "NE"},
                {"city": "Tempe", "state": "AZ"},
                {"city": "Las Vegas", "state": "NV"},
                {"city": "Portland", "state": "OR"}
            ],
            "services": [
                "Clinical Trials",
                "DMPK",
                "ADME",
                "Bioanalysis"
            ],
            "description": "Early clinical development CRO with Phase I units and bioanalytical services.",
            "tier": 2
        },
        {
            "id": "biotrial",
            "name": "Biotrial",
            "short_name": "Biotrial",
            "website": "biotrial.com",
            "is_medicilon": False,
            "states": ["NJ"],
            "cities": [
                {"city": "Newark", "state": "NJ"}
            ],
            "services": [
                "Clinical Trials",
                "DMPK",
                "Bioanalysis"
            ],
            "description": "European-origin CRO with Phase I clinical unit in the US.",
            "tier": 3
        },
        {
            "id": "medicilon",
            "name": "Medicilon",
            "short_name": "Medicilon",
            "website": "medicilon.com",
            "is_medicilon": True,
            "states": [],
            "cities": [],
            "services": [
                "In Vivo / Mouse Services",
                "DMPK",
                "ADME",
                "Toxicology",
                "Bioanalysis",
                "CMC",
                "Protein Sciences / Biologics"
            ],
            "description": "China-based integrated CRO with full preclinical capabilities, expanding to US market.",
            "note": "China-based CRO expanding to US market. No current US office presence.",
            "tier": 2,
            "core_services": [
                "In Vivo / Mouse Services",
                "DMPK",
                "ADME",
                "Toxicology",
                "Bioanalysis",
                "CMC"
            ]
        }
    ],
    "biotech_hub_weights": {
        "MA": 10, "CA": 10, "NJ": 9, "NC": 8, "TX": 8,
        "PA": 7, "NY": 7, "MD": 6, "IL": 6, "WA": 6,
        "CO": 5, "MN": 5, "GA": 4, "VA": 4, "FL": 4,
        "OH": 3, "MI": 3, "IN": 3, "WI": 3, "MO": 3,
        "KY": 2, "KS": 2, "NE": 2, "AZ": 2, "NV": 2, "OR": 2,
        "WV": 1, "ID": 1, "UT": 1, "NM": 1
    }
}

# ─── Service keyword matching for scraping ────────────────────────────────────

SERVICE_KEYWORDS = {
    "In Vivo / Mouse Services": [
        "in vivo", "mouse model", "xenograft", "pdx", "efficacy model",
        "animal model", "pharmacology model", "tumor model", "mouse services"
    ],
    "DMPK": [
        "dmpk", "drug metabolism", "pharmacokinetics", "pk study",
        "metabolite", "clearance", "half-life", "bioavailability"
    ],
    "ADME": [
        "adme", "absorption", "distribution", "metabolism", "excretion",
        "permeability", "caco-2", "microsome", "hepatocyte"
    ],
    "Toxicology": [
        "toxicology", "toxicity", "glp tox", "safety assessment",
        "genotoxicity", "ames test", "carcinogenicity", "regulatory tox"
    ],
    "Bioanalysis": [
        "bioanalysis", "lc-ms", "lc/ms", "immunoassay", "elisa",
        "pk/pd", "sample analysis", "bioanalytical", "mass spectrometry"
    ],
    "CMC": [
        "cmc", "chemistry manufacturing", "formulation", "drug substance",
        "drug product", "analytical chemistry", "stability", "scale-up"
    ],
    "Clinical Trials": [
        "clinical trial", "phase i", "phase 1", "phase ii", "phase 2",
        "phase iii", "phase iv", "clinical research", "clinical study"
    ],
    "Regulatory Affairs": [
        "regulatory", "fda submission", "ind filing", "nda", "bla",
        "regulatory strategy", "regulatory consulting"
    ],
    "Biomarker / Genomics": [
        "biomarker", "genomics", "proteomics", "transcriptomics",
        "ngs", "sequencing", "companion diagnostic", "omics"
    ],
    "Protein Sciences / Biologics": [
        "biologics", "protein science", "antibody", "protein expression",
        "recombinant protein", "cell line development", "biosimilar"
    ]
}

US_STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY"
}

STATE_ABBREVS = set(US_STATES.values())


def fetch_page(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch a webpage and return its text content."""
    if not SCRAPING_AVAILABLE:
        return None
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url}: {e}")
        return None


def extract_services(text: str) -> list[str]:
    """Match service keywords against page text."""
    text_lower = text.lower()
    found = []
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(service)
    return found


def extract_states(text: str) -> list[str]:
    """Extract US state abbreviations from text."""
    found = set()
    # Match full state names
    for name, abbrev in US_STATES.items():
        if name in text:
            found.add(abbrev)
    # Match state abbreviations in context (e.g., ", CA " or "CA,")
    pattern = r'\b([A-Z]{2})\b'
    candidates = re.findall(pattern, text)
    for c in candidates:
        if c in STATE_ABBREVS:
            found.add(c)
    return sorted(found)


def scrape_cro(cro: dict) -> dict:
    """Attempt to scrape a CRO website. Returns merged data with curated fallback."""
    website = cro.get("website", "")
    if not website or cro.get("is_medicilon"):
        return cro  # Don't scrape Medicilon

    url = f"https://www.{website}"
    print(f"  Scraping {cro['name']} ({url})...")

    html = fetch_page(url)
    if not html:
        print(f"  -> Using curated data for {cro['name']}")
        return cro

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    scraped_services = extract_services(text)
    scraped_states = extract_states(text)

    # Merge: prefer scraped data but fall back to curated if empty
    result = dict(cro)
    if scraped_services:
        print(f"  -> Found {len(scraped_services)} services via scraping")
        # Union of scraped + curated (curated is ground truth, scraping may add)
        merged_services = list(set(cro.get("services", [])) | set(scraped_services))
        result["services"] = merged_services
    else:
        print(f"  -> No services found via scraping, keeping curated")

    if scraped_states and len(scraped_states) > len(cro.get("states", [])):
        print(f"  -> Found {len(scraped_states)} states via scraping")
        # Use curated states (more accurate), scraping often pulls non-US content
        pass  # Keep curated states — scraping state data is unreliable

    result["scraped"] = bool(html)
    return result


def run_scraper(use_scraping: bool = True) -> dict:
    """Run scraper and return final data."""
    data = dict(CURATED_DATA)
    data["metadata"]["generated"] = str(date.today())

    if use_scraping and SCRAPING_AVAILABLE:
        print("\nAttempting to scrape CRO websites...")
        print("(Many sites are JS-heavy — curated data is used as authoritative fallback)\n")
        scraped_cros = []
        for cro in data["cros"]:
            scraped = scrape_cro(cro)
            scraped_cros.append(scraped)
            time.sleep(1.5)  # Be polite
        data["cros"] = scraped_cros
        data["metadata"]["source"] = "scraped+curated"
    else:
        print("Using curated data only.")
        data["metadata"]["source"] = "curated"

    return data


def save_data(data: dict, path: str = "data/cro_data.json") -> None:
    """Save data to JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {path}")


def print_summary(data: dict) -> None:
    """Print a summary of collected data."""
    print("\n" + "=" * 60)
    print("DATA SUMMARY")
    print("=" * 60)
    for cro in data["cros"]:
        states = cro.get("states", [])
        services = cro.get("services", [])
        marker = " [MEDICILON]" if cro.get("is_medicilon") else ""
        print(f"\n{cro['name']}{marker}")
        print(f"  States ({len(states)}): {', '.join(states) or 'None (China-based)'}")
        print(f"  Services ({len(services)}): {', '.join(services)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CRO competitive intelligence scraper")
    parser.add_argument(
        "--no-scrape",
        action="store_true",
        help="Skip web scraping, use curated data only"
    )
    parser.add_argument(
        "--output",
        default="data/cro_data.json",
        help="Output file path (default: data/cro_data.json)"
    )
    args = parser.parse_args()

    print("CRO Competitive Intelligence Scraper")
    print("=" * 40)

    data = run_scraper(use_scraping=not args.no_scrape)
    print_summary(data)
    save_data(data, args.output)
    print("\nDone. Open index.html in a browser (via local server) to view the map.")
    print("Tip: python -m http.server 8000  then visit http://localhost:8000")
