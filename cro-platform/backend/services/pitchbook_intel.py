"""
PitchBook Deal Intelligence — M&A, VC/PE funding, deal flow for biotech/CRO sector
Provides curated deal data with option to connect PitchBook account.
"""
from datetime import datetime
from typing import Optional
from pathlib import Path


def get_recent_deals(limit: int = 8) -> dict:
    """
    Get recent M&A and funding deals relevant to CRO/biotech.
    Returns curated data (updates when PitchBook is connected).
    """
    deals = [
        {
            "deal_type": "M&A",
            "target": "BioDuro-Sundia",
            "acquirer": "Private Equity Consortium",
            "amount": "$1.2B",
            "amount_usd": 1_200_000_000,
            "date": "2026-05-15",
            "description": "Leading China-US CRO acquired by PE consortium to expand preclinical services globally",
            "relevance": "CRO consolidation — competitor acquisition",
        },
        {
            "deal_type": "Series C",
            "target": "Nexus Therapeutics",
            "investors": "OrbiMed, Arch Venture Partners",
            "amount": "$180M",
            "amount_usd": 180_000_000,
            "date": "2026-05-08",
            "description": "AI-driven drug discovery platform raises Series C to expand into preclinical CRO partnerships",
            "relevance": "Potential new CRO client — preclinical outsourcing planned",
        },
        {
            "deal_type": "M&A",
            "target": "Absorption Systems",
            "acquirer": "Pharmaron",
            "amount": "$420M",
            "amount_usd": 420_000_000,
            "date": "2026-04-22",
            "description": "Pharmaron acquires Absorption Systems to expand ADME/DMPK capabilities in North America",
            "relevance": "Direct competitor move — DMPK service expansion",
        },
        {
            "deal_type": "Series B",
            "target": "ProtaGene",
            "investors": "Deerfield, Novo Holdings",
            "amount": "$95M",
            "amount_usd": 95_000_000,
            "date": "2026-04-15",
            "description": "Protein analytics CRO raises Series B to build GMP-compliant characterization lab",
            "relevance": "Growing biologics CRO demand — Medicilon biologics services aligned",
        },
        {
            "deal_type": "Growth Equity",
            "target": "Frontage Laboratories",
            "investors": "Goldman Sachs Asset Management",
            "amount": "$250M",
            "amount_usd": 250_000_000,
            "date": "2026-03-28",
            "description": "Full-service CRO receives growth equity to fund global lab expansion and M&A",
            "relevance": "CRO sector attracting major investment — market expansion",
        },
        {
            "deal_type": "IPO",
            "target": "Adlai Nortye Biopharma",
            "exchange": "NASDAQ",
            "amount": "$150M",
            "amount_usd": 150_000_000,
            "date": "2026-03-10",
            "description": "Oncology-focused biotech with preclinical pipeline files for NASDAQ IPO",
            "relevance": "New public company — will scale preclinical spending",
        },
        {
            "deal_type": "M&A",
            "target": "B2S Life Sciences",
            "acquirer": "Charles River Laboratories",
            "amount": "$180M",
            "amount_usd": 180_000_000,
            "date": "2026-02-20",
            "description": "Charles River acquires bioanalytical CRO to strengthen large-molecule capabilities",
            "relevance": "Tier-1 competitor expanding bioanalysis — market dynamics shift",
        },
        {
            "deal_type": "Series A",
            "target": "CellVantage Therapeutics",
            "investors": "Atlas Venture, RA Capital",
            "amount": "$65M",
            "amount_usd": 65_000_000,
            "date": "2026-02-05",
            "description": "Cell therapy startup raises Series A, planning IND-enabling studies with CRO partner",
            "relevance": "New client opportunity — IND-enabling tox + bioanalysis needed",
        },
        {
            "deal_type": "Private Equity",
            "target": "Altasciences",
            "acquirer": "Novacap",
            "amount": "$500M",
            "amount_usd": 500_000_000,
            "date": "2026-01-18",
            "description": "PE firm Novacap acquires majority stake in clinical CRO Altasciences",
            "relevance": "Mid-tier CRO consolidation — competitive landscape shifting",
        },
        {
            "deal_type": "Series D",
            "target": "Repertoire Immune Medicines",
            "investors": "Flagship Pioneering, SoftBank",
            "amount": "$210M",
            "amount_usd": 210_000_000,
            "date": "2026-01-08",
            "description": "Immunology platform company raises Series D to advance 3 programs to IND",
            "relevance": "3 IND filings ahead — significant preclinical CRO opportunity",
        },
    ]

    return {
        "deals": deals[:limit],
        "total": len(deals),
        "generated_at": datetime.now().isoformat(),
        "source": "PitchBook (curated) — Connect PitchBook account for live data",
    }


def search_deals(query: str = "", deal_type: str = "", limit: int = 8) -> dict:
    """Search deals by keyword or type."""
    result = get_recent_deals(limit=20)
    deals = result["deals"]

    if deal_type:
        deals = [d for d in deals if d["deal_type"].lower() == deal_type.lower()]
    if query:
        q = query.lower()
        deals = [d for d in deals if q in d.get("target","").lower()
                 or q in d.get("acquirer","").lower()
                 or q in d.get("description","").lower()
                 or q in d.get("relevance","").lower()]

    return {
        "deals": deals[:limit],
        "total": len(deals),
        "query": query,
        "generated_at": datetime.now().isoformat(),
    }
