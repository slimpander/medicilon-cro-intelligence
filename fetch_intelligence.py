#!/usr/bin/env python3
"""
CRO Market Intelligence Fetcher
Pulls live data from 3 free public APIs to identify potential CRO clients:

1. ClinicalTrials.gov API v2  — active trials by small biotech sponsors
2. SEC EDGAR Form D           — recent funding rounds (biotech/pharma)
3. NIH RePORTER API           — SBIR/STTR grants to small companies

Output: data/intelligence.json — consumed by the Potential Clients tab

Usage:
    python fetch_intelligence.py
    python fetch_intelligence.py --days 90    # look back 90 days (default 180)
    python fetch_intelligence.py --state MA   # filter to one state
"""

import json, os, re, time, argparse
from datetime import datetime, timedelta
from typing import Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("ERROR: pip install requests")
    exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
LOOKBACK_DAYS   = 180   # 6 months default
OUTPUT_PATH     = "data/intelligence.json"
MAX_PER_SOURCE  = 200   # cap per API

# Medicilon core services — used to score relevance
MEDICILON_SERVICES = [
    "In Vivo / Mouse Services", "DMPK", "ADME",
    "Toxicology", "Bioanalysis", "CMC", "Protein Sciences / Biologics"
]

# Therapeutic area → CRO service mapping
TA_TO_SERVICE = {
    "oncology":         ["In Vivo / Mouse Services", "Bioanalysis", "DMPK"],
    "cancer":           ["In Vivo / Mouse Services", "Bioanalysis", "DMPK"],
    "tumor":            ["In Vivo / Mouse Services", "DMPK"],
    "rare disease":     ["Toxicology", "Bioanalysis", "Regulatory Affairs"],
    "rare":             ["Toxicology", "Bioanalysis"],
    "cns":              ["DMPK", "Bioanalysis", "In Vivo / Mouse Services"],
    "neurology":        ["DMPK", "Bioanalysis", "In Vivo / Mouse Services"],
    "alzheimer":        ["DMPK", "Bioanalysis"],
    "immunology":       ["Bioanalysis", "Protein Sciences / Biologics"],
    "autoimmune":       ["Bioanalysis", "Toxicology"],
    "infectious":       ["DMPK", "ADME", "Toxicology"],
    "cardiovascular":   ["DMPK", "ADME", "In Vivo / Mouse Services"],
    "metabolic":        ["ADME", "DMPK", "In Vivo / Mouse Services"],
    "biologics":        ["Protein Sciences / Biologics", "Bioanalysis"],
    "antibody":         ["Protein Sciences / Biologics", "Bioanalysis"],
    "gene therapy":     ["Toxicology", "Bioanalysis", "Protein Sciences / Biologics"],
    "cell therapy":     ["Bioanalysis", "Protein Sciences / Biologics"],
    "adc":              ["Bioanalysis", "DMPK", "CMC"],
    "rna":              ["DMPK", "Toxicology", "CMC"],
    "small molecule":   ["DMPK", "ADME", "Toxicology"],
    "peptide":          ["DMPK", "CMC", "Bioanalysis"],
}

US_BIOTECH_HUBS = {
    "MA": 10, "CA": 10, "NJ": 9, "NC": 8, "TX": 8,
    "PA": 7,  "NY": 7,  "MD": 6, "IL": 6, "WA": 6,
    "CO": 5,  "MN": 5,  "GA": 4, "VA": 4, "FL": 4,
    "OH": 3,  "MI": 3,  "IN": 3, "WI": 3, "MO": 3,
}

STATE_ABBREV = {
    "Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA",
    "Colorado":"CO","Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA",
    "Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS",
    "Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA",
    "Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT",
    "Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM",
    "New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK",
    "Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC",
    "South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT",
    "Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY",
}

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

def score_lead(company: dict) -> int:
    """Score 0-100 based on hub weight, service match, signal strength."""
    hub_score  = US_BIOTECH_HUBS.get(company.get("state",""), 0) * 5
    svc_match  = len(set(company.get("needs",[])) & set(MEDICILON_SERVICES))
    svc_score  = svc_match * 10
    sig_score  = {"Phase I":20,"Phase I/II":20,"Phase II":30,"Phase III":25,
                  "Funding":15,"Grant":10,"Preclinical":10}.get(company.get("stage",""), 5)
    return min(100, hub_score + svc_score + sig_score)

def safe_get(url, params=None, timeout=20, retries=2):
    headers = {"User-Agent": "MedicionResearch/1.0 (market-intelligence-tool)"}
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 429:
                time.sleep(5 * (attempt+1)); continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries-1:
                print(f"  Request failed: {type(e).__name__}: {e}")
            else:
                time.sleep(3)
    return None

def safe_post(url, payload, timeout=20):
    headers = {"Content-Type": "application/json",
               "User-Agent": "MedicionResearch/1.0"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  POST failed: {type(e).__name__}: {e}")
        return None

# ── Source 1: ClinicalTrials.gov ──────────────────────────────────────────────
def fetch_clinical_trials(lookback_days=180, state_filter=None) -> list:
    """Fetch active industry-sponsored trials — Phase I/II = highest CRO need."""
    print("\n[1/3] ClinicalTrials.gov API...")
    results = []
    since = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    # Focus: industry-sponsored, Phase I/II, posted recently
    params = {
        "format": "json",
        "pageSize": 100,
        "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING,ACTIVE_NOT_RECRUITING",
        "filter.advanced": "AREA[LeadSponsorClass]INDUSTRY AND (AREA[Phase]PHASE1 OR AREA[Phase]PHASE2)",
        "fields": ",".join([
            "protocolSection.identificationModule",
            "protocolSection.statusModule",
            "protocolSection.sponsorCollaboratorsModule",
            "protocolSection.designModule",
            "protocolSection.conditionsModule",
            "protocolSection.contactsLocationsModule",
        ]),
        "sort": "LastUpdatePostDate:desc",
    }

    data = safe_get("https://clinicaltrials.gov/api/v2/studies", params=params)
    if not data:
        print("  ClinicalTrials.gov: no response")
        return []

    studies = data.get("studies", [])
    print(f"  Got {len(studies)} studies")

    seen = set()
    for s in studies:
        try:
            p = s.get("protocolSection", {})
            id_mod     = p.get("identificationModule", {})
            status_mod = p.get("statusModule", {})
            sponsor    = p.get("sponsorCollaboratorsModule", {})
            design     = p.get("designModule", {})
            conds      = p.get("conditionsModule", {})
            locs       = p.get("contactsLocationsModule", {})

            company_name = sponsor.get("leadSponsor", {}).get("name", "")
            if not company_name or company_name in seen: continue
            seen.add(company_name)

            nct_id    = id_mod.get("nctId", "")
            title     = id_mod.get("briefTitle", "")
            status    = status_mod.get("overallStatus", "")
            phases    = design.get("phases", [])
            phase_str = phases[0].replace("PHASE","Phase ") if phases else "N/A"
            conditions = conds.get("conditions", [])
            cond_text  = ", ".join(conditions[:3])

            # Extract US state from locations
            state = None
            for loc in locs.get("locations", []):
                loc_state = loc.get("state","")
                loc_country = loc.get("country","")
                if "United States" in loc_country or loc_country == "":
                    abbr = get_state_abbrev(loc_state)
                    if abbr and abbr in US_BIOTECH_HUBS:
                        state = abbr
                        break

            if state_filter and state != state_filter:
                continue

            start_date = status_mod.get("startDateStruct",{}).get("date","")
            posted_date = status_mod.get("studyFirstPostDateStruct",{}).get("date","")
            needs = infer_services(title + " " + cond_text)

            results.append({
                "source":     "ClinicalTrials.gov",
                "source_id":  nct_id,
                "name":       company_name,
                "state":      state or "US",
                "stage":      phase_str,
                "focus":      cond_text or title[:80],
                "needs":      needs,
                "signal":     f"{phase_str} trial — {status.replace('_',' ').title()}",
                "date":       posted_date or start_date,
                "url":        f"https://clinicaltrials.gov/study/{nct_id}",
                "score":      0,  # calculated after
            })
        except Exception as e:
            continue

    print(f"  Extracted {len(results)} US industry-sponsored trials")
    return results


# ── Source 2: SEC EDGAR Form D (Funding Rounds) ───────────────────────────────
def fetch_sec_funding(lookback_days=180, state_filter=None) -> list:
    """Fetch Form D filings — biotech/pharma companies that just raised money."""
    print("\n[2/3] SEC EDGAR Form D (funding rounds)...")
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
        "hits.hits.total.value": "true",
    }

    data = safe_get(url, params=params)
    if not data:
        print("  SEC EDGAR: no response")
        return []

    hits = data.get("hits",{}).get("hits",[])
    print(f"  Got {len(hits)} Form D filings")

    seen = set()
    for hit in hits[:MAX_PER_SOURCE]:
        try:
            src = hit.get("_source", {})
            names = src.get("display_names", [])
            if not names: continue

            # Parse "Company Name (CIK xxxxxxx)"
            raw_name = names[0]
            company_name = re.sub(r'\s*\(CIK.*?\)', '', raw_name).strip()
            if not company_name or company_name in seen: continue
            seen.add(company_name)

            # Skip fund vehicles
            skip_words = ['fund', 'lp', 'llc', 'partners', 'capital', 'ventures', 'management']
            if any(w in company_name.lower() for w in skip_words): continue

            biz_states = src.get("biz_states", [])
            state = None
            for bs in biz_states:
                abbr = get_state_abbrev(bs) if len(bs) > 2 else bs.upper()
                if abbr in US_BIOTECH_HUBS:
                    state = abbr
                    break

            if state_filter and state != state_filter: continue

            file_date = src.get("file_date","")
            adsh = src.get("adsh","")
            biz_loc = src.get("biz_locations",[""])[0]

            results.append({
                "source":    "SEC EDGAR",
                "source_id": adsh,
                "name":      company_name,
                "state":     state or "US",
                "stage":     "Funding",
                "focus":     f"Biopharma — {biz_loc}",
                "needs":     ["DMPK", "Toxicology", "Bioanalysis"],  # generic until enriched
                "signal":    f"Form D filed {file_date} — equity offering",
                "date":      file_date,
                "url":       f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={src.get('ciks',[''])[0]}&type=D&dateb=&owner=include&count=10",
                "score":     0,
            })
        except Exception:
            continue

    print(f"  Extracted {len(results)} biotech funding events")
    return results


# ── Source 3: NIH RePORTER (SBIR/STTR Grants) ────────────────────────────────
def fetch_nih_grants(lookback_days=180, state_filter=None) -> list:
    """Fetch SBIR/STTR grants — small companies with NIH funding = early pipeline."""
    print("\n[3/3] NIH RePORTER API...")
    results = []
    since_year = (datetime.now() - timedelta(days=lookback_days)).year
    fiscal_years = list(set([since_year, since_year+1, datetime.now().year]))

    payload = {
        "criteria": {
            "fiscal_years": fiscal_years,
            "award_types": ["1", "2", "3", "4"],  # SBIR/STTR type codes
            "activity_codes": ["R41", "R42", "R43", "R44", "SB1", "ST1"],
            "org_countries": ["UNITED STATES"],
        },
        "limit": 100,
        "offset": 0,
        "sort_field": "project_start_date",
        "sort_order": "desc",
        "include_fields": [
            "project_title", "organization", "fiscal_year",
            "award_amount", "project_start_date", "project_end_date",
            "phr_text", "terms", "appl_id"
        ]
    }

    if state_filter:
        payload["criteria"]["org_states"] = [state_filter]

    data = safe_post("https://api.reporter.nih.gov/v2/projects/search", payload)
    if not data:
        print("  NIH RePORTER: no response")
        return []

    projects = data.get("results", [])
    print(f"  Got {len(projects)} NIH grants")

    seen = set()
    for p in projects:
        try:
            org = p.get("organization", {})
            company_name = org.get("org_name","").strip().title()
            if not company_name or company_name in seen: continue
            seen.add(company_name)

            # Skip universities/hospitals
            skip = ['university','college','hospital','institute','school','center',
                    'foundation','government','department']
            if any(w in company_name.lower() for w in skip): continue

            state = org.get("org_state","")
            if state and len(state) == 2:
                state = state.upper()
            else:
                state = get_state_abbrev(state) or "US"

            if state_filter and state != state_filter: continue

            title     = p.get("project_title","")
            phr       = p.get("phr_text","") or ""
            terms     = " ".join(p.get("terms","") or [])
            amount    = p.get("award_amount",0) or 0
            start     = (p.get("project_start_date","") or "")[:10]
            appl_id   = p.get("appl_id","")
            needs     = infer_services(title + " " + phr + " " + terms)

            amount_str = f"${amount:,.0f}" if amount else "undisclosed"

            results.append({
                "source":    "NIH RePORTER",
                "source_id": str(appl_id),
                "name":      company_name,
                "state":     state,
                "stage":     "Grant",
                "focus":     title[:100],
                "needs":     needs,
                "signal":    f"NIH SBIR/STTR award {amount_str} ({p.get('fiscal_year','')})",
                "date":      start,
                "url":       f"https://reporter.nih.gov/project-details/{appl_id}",
                "score":     0,
            })
        except Exception:
            continue

    print(f"  Extracted {len(results)} small company NIH grants")
    return results


# ── Dedup + Score + Save ──────────────────────────────────────────────────────
def deduplicate(leads: list) -> list:
    seen = {}
    result = []
    for lead in leads:
        key = re.sub(r'\W+','',lead["name"].lower())[:20]
        if key not in seen:
            seen[key] = True
            result.append(lead)
    return result

def enrich_and_score(leads: list) -> list:
    for lead in leads:
        lead["score"] = score_lead(lead)
        lead["hub_weight"] = US_BIOTECH_HUBS.get(lead.get("state",""), 0)
        # Format date nicely
        d = lead.get("date","")
        if d:
            try:
                dt = datetime.strptime(d[:10], "%Y-%m-%d")
                delta = datetime.now() - dt
                if delta.days == 0: lead["date_label"] = "today"
                elif delta.days < 7: lead["date_label"] = f"{delta.days}d ago"
                elif delta.days < 30: lead["date_label"] = f"{delta.days//7}w ago"
                elif delta.days < 365: lead["date_label"] = f"{delta.days//30}mo ago"
                else: lead["date_label"] = f"{delta.days//365}y ago"
            except: lead["date_label"] = d
        else:
            lead["date_label"] = "unknown"
    # Sort by score desc
    return sorted(leads, key=lambda x: x["score"], reverse=True)

def save(leads: list, lookback_days: int):
    os.makedirs("data", exist_ok=True)
    out = {
        "metadata": {
            "generated":     datetime.now().isoformat(),
            "lookback_days": lookback_days,
            "total":         len(leads),
            "sources": {
                "clinical_trials": sum(1 for l in leads if l["source"]=="ClinicalTrials.gov"),
                "sec_funding":     sum(1 for l in leads if l["source"]=="SEC EDGAR"),
                "nih_grants":      sum(1 for l in leads if l["source"]=="NIH RePORTER"),
            }
        },
        "leads": leads
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(leads)} leads to {OUTPUT_PATH}")

def print_summary(leads: list):
    print("\n" + "="*60)
    print("INTELLIGENCE SUMMARY")
    print("="*60)
    print(f"Total leads: {len(leads)}")
    by_source = {}
    by_state  = {}
    by_stage  = {}
    for l in leads:
        by_source[l["source"]] = by_source.get(l["source"],0) + 1
        by_state[l["state"]]   = by_state.get(l["state"],0) + 1
        by_stage[l["stage"]]   = by_stage.get(l["stage"],0) + 1

    print("\nBy source:")
    for k,v in sorted(by_source.items(), key=lambda x:-x[1]):
        print(f"  {k}: {v}")
    print("\nTop states:")
    for k,v in sorted(by_state.items(), key=lambda x:-x[1])[:8]:
        print(f"  {k}: {v}")
    print("\nBy stage:")
    for k,v in sorted(by_stage.items(), key=lambda x:-x[1]):
        print(f"  {k}: {v}")
    print(f"\nTop 5 leads:")
    for l in leads[:5]:
        print(f"  [{l['score']:3d}] {l['name'][:40]:40s} | {l['state']} | {l['stage']} | {l['signal'][:50]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CRO Market Intelligence Fetcher")
    parser.add_argument("--days",  type=int, default=180, help="Lookback days (default 180)")
    parser.add_argument("--state", type=str, default=None, help="Filter to US state abbrev (e.g. MA)")
    args = parser.parse_args()

    print(f"CRO Market Intelligence Fetcher")
    print(f"Lookback: {args.days} days | State filter: {args.state or 'all US'}")
    print("="*60)

    all_leads = []
    all_leads += fetch_clinical_trials(args.days, args.state)
    all_leads += fetch_sec_funding(args.days, args.state)
    all_leads += fetch_nih_grants(args.days, args.state)

    all_leads = deduplicate(all_leads)
    all_leads = enrich_and_score(all_leads)

    print_summary(all_leads)
    save(all_leads, args.days)
    print("\nDone. Now update the platform:")
    print("  python patch_intelligence.py")
