"""
Enhanced Funding Intelligence Fetcher
Combines SEC EDGAR, ClinicalTrials.gov, NIH RePORTER, AND Crunchbase into
a unified intelligence pipeline with enriched metadata (funding amounts, investors, etc.)

Usage:
    python -m backend.services.funding_fetcher --days 90
    python -m backend.services.funding_fetcher --crunchbase-key YOUR_KEY
"""

import json
import os
import sys
import time
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import requests

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DATA = BASE_DIR / "frontend" / "data"
OUTPUT_PATH = FRONTEND_DATA / "intelligence.json"
LOOKBACK_DAYS = 180
MAX_PER_SOURCE = 200

US_BIOTECH_HUBS = {
    "MA": 10, "CA": 10, "NJ": 9, "NC": 8, "TX": 8,
    "PA": 7, "NY": 7, "MD": 6, "IL": 6, "WA": 6,
    "CO": 5, "MN": 5, "GA": 4, "VA": 4, "FL": 4,
    "OH": 3, "MI": 3, "IN": 3, "WI": 3, "MO": 3,
}

MEDICILON_SERVICES = [
    "In Vivo / Mouse Services", "DMPK", "ADME",
    "Toxicology", "Bioanalysis", "CMC", "Protein Sciences / Biologics"
]

TA_TO_SERVICE = {
    "oncology": ["In Vivo / Mouse Services", "Bioanalysis", "DMPK"],
    "cancer": ["In Vivo / Mouse Services", "Bioanalysis", "DMPK"],
    "tumor": ["In Vivo / Mouse Services", "DMPK"],
    "rare disease": ["Toxicology", "Bioanalysis"],
    "cns": ["DMPK", "Bioanalysis", "In Vivo / Mouse Services"],
    "neurology": ["DMPK", "Bioanalysis", "In Vivo / Mouse Services"],
    "alzheimer": ["DMPK", "Bioanalysis"],
    "immunology": ["Bioanalysis", "Protein Sciences / Biologics"],
    "autoimmune": ["Bioanalysis", "Toxicology"],
    "infectious": ["DMPK", "ADME", "Toxicology"],
    "cardiovascular": ["DMPK", "ADME", "In Vivo / Mouse Services"],
    "metabolic": ["ADME", "DMPK", "In Vivo / Mouse Services"],
    "biologics": ["Protein Sciences / Biologics", "Bioanalysis"],
    "antibody": ["Protein Sciences / Biologics", "Bioanalysis"],
    "gene therapy": ["Toxicology", "Bioanalysis", "Protein Sciences / Biologics"],
    "cell therapy": ["Bioanalysis", "Protein Sciences / Biologics"],
    "adc": ["Bioanalysis", "DMPK", "CMC"],
    "rna": ["DMPK", "Toxicology", "CMC"],
    "small molecule": ["DMPK", "ADME", "Toxicology"],
    "peptide": ["DMPK", "CMC", "Bioanalysis"],
}

STATE_ABBREV = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_state_abbrev(text: str) -> Optional[str]:
    if not text: return None
    text = text.strip()
    if len(text) == 2 and text.upper() in US_BIOTECH_HUBS:
        return text.upper()
    return STATE_ABBREV.get(text)


def infer_services(text: str) -> list:
    text_lower = text.lower()
    services = set()
    for kw, svcs in TA_TO_SERVICE.items():
        if kw in text_lower:
            services.update(svcs)
    return sorted(services) or ["DMPK", "Bioanalysis"]


def safe_get(url, params=None, timeout=20, retries=2):
    headers = {"User-Agent": "MedicilonResearch/1.0 (market-intelligence-tool)"}
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json() if "application/json" in r.headers.get("content-type", "") else r.text
        except Exception as e:
            if attempt == retries - 1:
                print(f"  Request failed: {type(e).__name__}: {e}")
            else:
                time.sleep(3)
    return None


# ── Source 1: ClinicalTrials.gov ──────────────────────────────────────────────

def fetch_clinical_trials(lookback_days=180, state_filter=None) -> list:
    print("\n[1/4] ClinicalTrials.gov API...")
    results = []
    since = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    params = {
        "format": "json",
        "pageSize": 100,
        "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING,ACTIVE_NOT_RECRUITING",
        "filter.advanced": "AREA[LeadSponsorClass]INDUSTRY AND (AREA[Phase]PHASE1 OR AREA[Phase]PHASE2)",
        "fields": "protocolSection.identificationModule,protocolSection.statusModule,protocolSection.sponsorCollaboratorsModule,protocolSection.designModule,protocolSection.conditionsModule,protocolSection.contactsLocationsModule",
        "sort": "LastUpdatePostDate:desc",
    }

    data = safe_get("https://clinicaltrials.gov/api/v2/studies", params=params)
    if not data:
        print("  ClinicalTrials.gov: no response")
        return []

    studies = data.get("studies", [])
    print(f"  Got {len(studies)} studies")

    seen = set()
    for s in studies[:MAX_PER_SOURCE]:
        try:
            p = s.get("protocolSection", {})
            id_mod = p.get("identificationModule", {})
            status_mod = p.get("statusModule", {})
            sponsor = p.get("sponsorCollaboratorsModule", {})
            design = p.get("designModule", {})
            conds = p.get("conditionsModule", {})
            locs = p.get("contactsLocationsModule", {})

            company_name = sponsor.get("leadSponsor", {}).get("name", "")
            if not company_name or company_name in seen: continue
            seen.add(company_name)

            nct_id = id_mod.get("nctId", "")
            title = id_mod.get("briefTitle", "")
            phases = design.get("phases", [])
            phase_str = phases[0].replace("PHASE", "Phase ") if phases else "N/A"
            conditions = conds.get("conditions", [])
            cond_text = ", ".join(conditions[:3])

            state = None
            city = None
            for loc in locs.get("locations", []):
                loc_state = loc.get("state", "")
                loc_country = loc.get("country", "")
                if "United States" in loc_country or loc_country == "":
                    abbr = get_state_abbrev(loc_state)
                    if abbr and abbr in US_BIOTECH_HUBS:
                        state = abbr
                        city = loc.get("city", "")
                        break

            if state_filter and state != state_filter:
                continue

            posted_date = status_mod.get("studyFirstPostDateStruct", {}).get("date", "")
            needs = infer_services(title + " " + cond_text)

            results.append({
                "source": "ClinicalTrials.gov",
                "source_id": nct_id,
                "name": company_name,
                "state": state or "US",
                "city": city or "",
                "stage": phase_str,
                "focus": cond_text or title[:80],
                "needs": needs,
                "signal": f"{phase_str} trial",
                "date": posted_date,
                "url": f"https://clinicaltrials.gov/study/{nct_id}",
            })
        except Exception:
            continue

    print(f"  Extracted {len(results)} US industry-sponsored trials")
    return results


# ── Source 2: SEC EDGAR Form D ────────────────────────────────────────────────

def fetch_sec_funding(lookback_days=180, state_filter=None) -> list:
    print("\n[2/4] SEC EDGAR Form D (funding rounds)...")
    results = []
    since = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "q": '"biotech" OR "biopharmaceutical" OR "therapeutics" OR "biopharma"',
        "dateRange": "custom",
        "startdt": since,
        "enddt": today,
        "forms": "D",
    }

    data = safe_get(url, params=params)
    if not data:
        print("  SEC EDGAR: no response")
        return []

    hits = data.get("hits", {}).get("hits", [])
    print(f"  Got {len(hits)} Form D filings")

    seen = set()
    for hit in hits[:MAX_PER_SOURCE]:
        try:
            src = hit.get("_source", {})
            names = src.get("display_names", [])
            if not names: continue

            raw_name = names[0]
            company_name = re.sub(r'\s*\(CIK.*?\)', '', raw_name).strip()
            if not company_name or company_name in seen: continue
            seen.add(company_name)

            skip_words = ['fund', 'lp', 'llc', 'partners', 'capital', 'ventures', 'management']
            if any(w in company_name.lower() for w in skip_words): continue

            # Extract CIK: try ciks[] array first, then parse from display_names string
            ciks_list = src.get('ciks', [])
            cik = str(ciks_list[0]) if ciks_list else ''
            if not cik:
                m = re.search(r'CIK\s+(\d+)', raw_name)
                cik = m.group(1) if m else ''

            biz_states = src.get("biz_states", [])
            state = None
            for bs in biz_states:
                abbr = get_state_abbrev(bs) if len(bs) > 2 else bs.upper()
                if abbr in US_BIOTECH_HUBS:
                    state = abbr
                    break

            if state_filter and state != state_filter: continue

            file_date = src.get("file_date", "")
            biz_loc = src.get("biz_locations", [""])[0]

            results.append({
                "source": "SEC EDGAR",
                "source_id": src.get("adsh", company_name),
                "name": company_name,
                "state": state or "US",
                "city": biz_loc.split(",")[0].strip() if "," in biz_loc else "",
                "stage": "Funding",
                "focus": f"Biopharma — {biz_loc}" if biz_loc else "Biopharma",
                "needs": ["DMPK", "Toxicology", "Bioanalysis"],
                "signal": f"Form D filed {file_date} — equity offering",
                "date": file_date,
                "url": (
                    f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=D&dateb=&owner=include&count=10"
                    if cik else
                    f"https://efts.sec.gov/LATEST/search-index?q=%22{company_name}%22&forms=D"
                ),
            })
        except Exception:
            continue

    print(f"  Extracted {len(results)} Form D filings")
    return results


# ── Source 3: NIH RePORTER ────────────────────────────────────────────────────

def fetch_nih_grants(lookback_days=180, state_filter=None) -> list:
    print("\n[3/4] NIH RePORTER (SBIR/STTR grants)...")
    results = []

    payload = {
        "criteria": {
            "fiscal_years": [datetime.now().year, datetime.now().year - 1],
            "activity_codes": ["R41", "R42", "R43", "R44"],
        },
        "offset": 0,
        "limit": 50,
    }

    data = safe_get("https://api.reporter.nih.gov/v2/projects/search",
                     payload, timeout=30) if hasattr(requests, 'post') else safe_get(
                         "https://api.reporter.nih.gov/v2/projects/search",
                         params={"criteria": json.dumps(payload["criteria"])})

    try:
        data = requests.post(
            "https://api.reporter.nih.gov/v2/projects/search",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        ).json()
    except Exception as e:
        print(f"  NIH RePORTER error: {e}")
        return []

    projects = data.get("results", [])
    print(f"  Got {len(projects)} SBIR/STTR grants")
    seen = set()
    for proj in projects[:MAX_PER_SOURCE]:
        try:
            org = proj.get("organization", {})
            company_name = org.get("org_name", "")
            if not company_name or company_name in seen: continue
            seen.add(company_name)

            org_state = org.get("org_state", "")
            state = org_state if org_state in US_BIOTECH_HUBS else None
            if state_filter and state != state_filter: continue

            title = proj.get("project_title", "")
            needs = infer_services(title)
            fy = proj.get("fiscal_year", "")

            results.append({
                "source": "NIH RePORTER",
                "source_id": str(proj.get("appl_id", company_name)),
                "name": company_name,
                "state": state or org_state or "US",
                "city": org.get("org_city", ""),
                "stage": "Grant",
                "focus": title[:100],
                "needs": needs,
                "signal": f"SBIR/STTR grant FY{fy}",
                "date": f"{fy}-01-01",
                "url": f"https://reporter.nih.gov/search/results?projects=active",
            })
        except Exception:
            continue

    print(f"  Extracted {len(results)} NIH grants")
    return results


# ── Source 4: Crunchbase (new!) ───────────────────────────────────────────────

def fetch_crunchbase(api_key: str, lookback_days=90, state_filter=None) -> list:
    """Fetch recently funded biotech companies from Crunchbase."""
    print(f"\n[4/4] Crunchbase API (past {lookback_days} days)...")

    if not api_key:
        print("  No Crunchbase API key provided — skipping")
        return []

    try:
        from services.crunchbase_client import CrunchbaseClient
    except ImportError:
        sys.path.insert(0, str(BASE_DIR / "backend"))
        from services.crunchbase_client import CrunchbaseClient

    client = CrunchbaseClient(api_key=api_key)
    leads = client.discover_recently_funded(
        days_back=lookback_days,
        min_amount_usd=1_000_000,
        states=list(US_BIOTECH_HUBS.keys()) if not state_filter else [state_filter],
        limit=100,
    )

    print(f"  Crunchbase: {len(leads)} recently funded companies")
    return leads


# ── Merge + Score + Save ──────────────────────────────────────────────────────

def deduplicate(leads: list) -> list:
    """Deduplicate leads by normalized company name."""
    seen = {}
    result = []
    for lead in leads:
        key = re.sub(r'[^a-z0-9]', '', lead.get("name", "").lower())[:30]
        if key and key not in seen:
            seen[key] = True
            # Prefer Crunchbase entries (richer data)
            result.append(lead)
        elif key and lead.get("source") == "Crunchbase":
            # Replace existing with richer Crunchbase data
            for i, existing in enumerate(result):
                ek = re.sub(r'[^a-z0-9]', '', existing.get("name", "").lower())[:30]
                if ek == key:
                    result[i] = lead
                    break
    return result


def enrich_and_score(leads: list) -> list:
    """Add scores, hub weights, and formatted date labels."""
    for lead in leads:
        hub_w = US_BIOTECH_HUBS.get(lead.get("state", ""), 0)
        svc_match = len(set(lead.get("needs", [])) & set(MEDICILON_SERVICES))
        sig_score = {
            "Phase 1": 20, "Phase 1/II": 20, "Phase 2": 30, "Phase 3": 25,
            "Funding": 20, "Seed/Funding": 15, "Public": 10,
            "Grant": 10, "Preclinical": 10,
        }.get(lead.get("stage", ""), 5)

        # Bonus for large funding rounds (bigger budget = more CRO spend)
        amount = lead.get("recent_round_amount_usd", 0) or lead.get("total_funding_usd", 0)
        amount_bonus = 0
        if amount >= 100_000_000: amount_bonus = 15  # $100M+
        elif amount >= 50_000_000: amount_bonus = 10
        elif amount >= 10_000_000: amount_bonus = 5

        lead["score"] = min(100, hub_w * 5 + svc_match * 10 + sig_score + amount_bonus)
        lead["hub_weight"] = hub_w

        # Format date label
        d = lead.get("date", "")
        if d:
            try:
                dt = datetime.strptime(d[:10], "%Y-%m-%d")
                delta = datetime.now() - dt
                if delta.days == 0: lead["date_label"] = "today"
                elif delta.days < 7: lead["date_label"] = f"{delta.days}d ago"
                elif delta.days < 30: lead["date_label"] = f"{delta.days // 7}w ago"
                elif delta.days < 365: lead["date_label"] = f"{delta.days // 30}mo ago"
                else: lead["date_label"] = f"{delta.days // 365}y ago"
            except Exception:
                lead["date_label"] = d
        else:
            lead["date_label"] = "unknown"

    return sorted(leads, key=lambda x: x["score"], reverse=True)


def save(leads: list, lookback_days: int, crunchbase_used: bool = False):
    """Save to frontend data directory."""
    FRONTEND_DATA.mkdir(parents=True, exist_ok=True)

    sources = {
        "clinical_trials": sum(1 for l in leads if l["source"] == "ClinicalTrials.gov"),
        "sec_funding": sum(1 for l in leads if l["source"] == "SEC EDGAR"),
        "nih_grants": sum(1 for l in leads if l["source"] == "NIH RePORTER"),
        "crunchbase": sum(1 for l in leads if l["source"] == "Crunchbase"),
    }

    out = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "lookback_days": lookback_days,
            "total": len(leads),
            "sources": sources,
            "crunchbase_enabled": crunchbase_used,
        },
        "leads": leads,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(leads)} leads to {OUTPUT_PATH}")


def print_summary(leads: list):
    print("\n" + "=" * 60)
    print("INTELLIGENCE SUMMARY")
    print("=" * 60)
    print(f"Total leads: {len(leads)}")

    by_source = {}
    by_state = {}
    total_funding = 0
    for l in leads:
        by_source[l["source"]] = by_source.get(l["source"], 0) + 1
        by_state[l["state"]] = by_state.get(l["state"], 0) + 1
        total_funding += (l.get("total_funding_usd", 0) or 0)

    print("\nBy source:")
    for k, v in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    print("\nTop states:")
    for k, v in sorted(by_state.items(), key=lambda x: -x[1])[:8]:
        print(f"  {k}: {v}")

    if total_funding > 0:
        print(f"\nTotal funding tracked: ${total_funding / 1e9:.1f}B")

    print(f"\nTop 10 leads:")
    for l in leads[:10]:
        amount_str = ""
        if l.get("recent_round_amount_display"):
            amount_str = f" [{l['recent_round_amount_display']}]"
        elif l.get("total_funding_display"):
            amount_str = f" [total: {l['total_funding_display']}]"
        print(f"  [{l['score']:3d}] {l['name'][:40]:40s} | {l['state']} | {l['source'][:18]:18s} | {l['stage']}{amount_str}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced Funding Intelligence Fetcher")
    parser.add_argument("--days", type=int, default=180, help="Lookback days")
    parser.add_argument("--state", type=str, default=None, help="Filter to US state")
    parser.add_argument("--crunchbase-key", type=str, default="", help="Crunchbase API key")
    parser.add_argument("--no-crunchbase", action="store_true", help="Skip Crunchbase")
    parser.add_argument("--output", type=str, default="", help="Custom output path")
    args = parser.parse_args()

    if args.output:
        OUTPUT_PATH = Path(args.output)

    print(f"Enhanced Funding Intelligence Fetcher")
    print(f"Lookback: {args.days} days | State filter: {args.state or 'all US'}")
    print(f"Crunchbase: {'enabled' if args.crunchbase_key else 'disabled'}")
    print("=" * 60)

    all_leads = []
    all_leads += fetch_clinical_trials(args.days, args.state)
    all_leads += fetch_sec_funding(args.days, args.state)
    all_leads += fetch_nih_grants(args.days, args.state)

    crunchbase_used = False
    if not args.no_crunchbase and args.crunchbase_key:
        all_leads += fetch_crunchbase(args.crunchbase_key, min(args.days, 90), args.state)
        crunchbase_used = True

    all_leads = deduplicate(all_leads)
    all_leads = enrich_and_score(all_leads)

    print_summary(all_leads)
    save(all_leads, args.days, crunchbase_used)

    print("\nDone! Refresh the dashboard to see updated leads.")
    print(f"  Data file: {OUTPUT_PATH}")
