"""
LinkedIn Intelligence Aggregator — Backend-driven BD signal collection
Replaces browser-based LinkedIn scraping with automated multi-source aggregation.
No LinkedIn account or browser needed. Runs on schedule.

Sources:
  1. Google News RSS — biotech funding, CRO partnerships, hiring, clinical milestones
  2. BioPharma Dive / FierceBiotech RSS — industry deals and movements
  3. SEC EDGAR Form D — funding rounds (high signal for CRO readiness)
  4. ClinicalTrials.gov — newly posted industry trials (CRO opportunity signal)

Output: structured posts compatible with linkedin_posts scoring pipeline
"""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "platform.db"

# ── Signal Categories (mirrors LinkedIn keyword categories) ───────────────────

CATEGORIES = {
    "cro_outsourcing": {
        "label": "CRO Outsourcing",
        "keywords": [
            "CRO partner", "CRO partnership", "select.*CRO", "awarded.*CRO",
            "outsourcing", "contract research organization", "preclinical CRO",
            "CDMO partner", "contract manufacturing", "RFP.*CRO", "CRO.*RFP",
            "looking for.*CRO", "seeking.*CRO", "CRO support", "preferred.*CRO",
            "CRO network", "outsource", "CRO capabilities", "CRO services",
        ],
        "weight": 3.0,  # Highest signal — direct spending intent
    },
    "funding_milestone": {
        "label": "Funding & Milestones",
        "keywords": [
            "raised", "raises", "secured.*financing", "closes.*million",
            "closes.*billion", "series a", "series b", "series c", "series d",
            "seed round", "venture capital", "funding round", "IPO", "public offering",
            "IND filing", "IND submission", "IND cleared", "FDA clearance",
            "Phase 1", "Phase 2", "Phase 3", "pivotal trial", "NDA submission",
        ],
        "weight": 2.5,
    },
    "drug_development": {
        "label": "Drug Development",
        "keywords": [
            "preclinical", "drug discovery", "lead candidate", "pipeline",
            "small molecule", "antibody", "biologic", "cell therapy", "gene therapy",
            "mRNA", "ADC", "PROTAC", "bispecific", "oncology", "immunology",
            "DMPK", "ADME", "pharmacokinetics", "toxicology", "bioanalysis",
            "CMC", "formulation", "manufacturing", "IND-enabling",
        ],
        "weight": 1.5,
    },
    "decision_maker": {
        "label": "Decision Maker Activity",
        "keywords": [
            "CSO", "Chief Scientific Officer", "VP R&D", "VP Research",
            "Head of Preclinical", "Head of DMPK", "Head of Pharmacology",
            "Director of Toxicology", "SVP Discovery", "CEO", "CTO",
            "Head of Outsourcing", "Director CMC", "VP Chemistry",
            "appointed", "named", "joins", "hired", "announces",
        ],
        "weight": 2.0,
    },
    "partnerships": {
        "label": "Partnerships & Deals",
        "keywords": [
            "partnership", "collaboration", "strategic alliance",
            "licensing deal", "license agreement", "merger", "acquisition",
            "acquired", "merges", "joint venture", "co-development",
            "exclusive license", "option agreement",
        ],
        "weight": 2.0,
    },
}

# Title keyword patterns for decision-maker detection
DECISION_MAKER_TITLES = [
    r'\b(CSO|CEO|CTO|CFO|COO)\b',
    r'\b(Chief\s+\w+\s+Officer)\b',
    r'\b(VP|SVP|EVP)\s+(of\s+)?(Research|Development|Discovery|R&D|Preclinical|Clinical|DMPK|Chemistry|Biology|Pharmacology|Operations|Outsourcing|CMC|Manufacturing)\b',
    r'\b(Head\s+of\s+(Preclinical|DMPK|Pharmacology|Outsourcing|Chemistry|Biology|Research|Development|Bioanalysis|CMC|Toxicology))\b',
    r'\b(Director\s+of\s+(Preclinical|DMPK|Toxicology|Pharmacology|Outsourcing|Chemistry|CMC|Bioanalysis|Biology))\b',
    r'\b(Senior\s+Director|Executive\s+Director|Associate\s+Director)\b',
    r'\b(Founder|Co-founder)\b',
    r'\b(President)\b',
]


# ── Fetch Functions ───────────────────────────────────────────────────────────

def _safe_fetch(url, timeout=15, retries=2):
    """Fetch URL with retries and polite delays."""
    if not HAS_DEPS:
        return None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, text/html",
    }
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(3)
    return None


def _parse_rss_date(pub_str: str) -> Optional[str]:
    if not pub_str:
        return datetime.now().isoformat()
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(pub_str).replace(tzinfo=None).isoformat()
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(pub_str, fmt).isoformat()
        except Exception:
            continue
    return pub_str[:10] if pub_str else datetime.now().isoformat()


def _score_signal(text: str) -> tuple:
    """Score a text against BD signal categories. Returns (score, matched_keywords, tier)."""
    text_lower = text.lower()
    total = 0.0
    matched = []
    categories_matched = []

    for cat_key, cat_info in CATEGORIES.items():
        cat_matches = []
        for kw in cat_info["keywords"]:
            if re.search(kw, text_lower):
                cat_matches.append(kw)

        if cat_matches:
            total += cat_info["weight"] * min(len(cat_matches), 5)
            matched.extend(cat_matches[:3])
            categories_matched.append(cat_info["label"])

    # Normalize to 0-100
    score = min(95, total * 8)

    # Tier classification
    if score >= 70:
        tier = "S"
    elif score >= 50:
        tier = "A"
    elif score >= 30:
        tier = "B"
    elif score >= 10:
        tier = "C"
    else:
        tier = "D"

    return score, matched[:5], tier


def _detect_decision_maker(title_text: str, full_text: str) -> tuple:
    """Detect decision-maker titles. Returns (is_dm, title_found, company)."""
    combined = (title_text + " " + full_text)
    for pattern in DECISION_MAKER_TITLES:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            title_found = match.group(0)
            # Try to extract company name
            company = ""
            company_patterns = [
                r'(?:at|from|of)\s+([A-Z][A-Za-z0-9\s&\-.]+?)(?:[,.]|\s+(?:announced|raised|secured|closed|appointed|named|selected|is|has|will|today))',
                r'([A-Z][A-Za-z0-9\s]+(?:Therapeutics|Biotech|Pharma|Bio|Sciences|Labs|Laboratories))(?:[,.]|\s)',
                r'CEO\s+(?:of|at)\s+([A-Z][A-Za-z0-9\s&\-.]+?)(?:[,.]|\s+(?:announced|raised|secured|closed))',
            ]
            for cp in company_patterns:
                cm = re.search(cp, combined, re.IGNORECASE)
                if cm:
                    company = cm.group(1).strip()
                    break
            return True, title_found, company
    return False, "", ""


# ── Source 1: Google News RSS — Biotech Keywords ──────────────────────────────

def fetch_google_news_biotech(max_results: int = 40) -> list:
    """Fetch biotech/CRO related articles from Google News RSS."""
    results = []

    # Multiple keyword searches to cover different signal categories
    search_queries = [
        # CRO outsourcing signals
        (
            "CRO OR CDMO partnership biotech preclinical outsourcing",
            "cro_outsourcing"
        ),
        # Funding signals
        (
            "biotech raises funding series IPO investment IND filing",
            "funding_milestone"
        ),
        # Drug development
        (
            "preclinical OR DMPK OR toxicology OR bioanalysis CRO support drug development",
            "drug_development"
        ),
        # Partnerships & M&A
        (
            "biotech partnership OR acquisition OR merger OR collaboration CRO",
            "partnerships"
        ),
    ]

    for query, category in search_queries:
        encoded = requests.utils.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

        resp = _safe_fetch(url)
        if not resp:
            continue

        try:
            soup = BeautifulSoup(resp.text, "xml")
            items = soup.find_all("item")

            for item in items[:15]:
                title_tag = item.find("title")
                title = title_tag.get_text(strip=True) if title_tag else ""
                if not title or len(title) < 10:
                    continue

                # Parse source from title (Google News format: "Title - Source")
                source = "Google News"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    if len(parts) == 2 and len(parts[1]) < 50:
                        title = parts[0]
                        source = parts[1]

                # Date
                pub_tag = item.find("pubDate")
                date_iso = _parse_rss_date(pub_tag.get_text(strip=True) if pub_tag else "")

                # Description
                desc_tag = item.find("description")
                desc = ""
                if desc_tag:
                    raw = desc_tag.get_text(strip=True)
                    desc = BeautifulSoup(raw, "html.parser").get_text(strip=True)[:500]

                # Link
                link_tag = item.find("link")
                url_val = link_tag.get_text(strip=True) if link_tag else ""

                full_text = f"{title} {desc}"
                score, keywords, tier = _score_signal(full_text)

                if score < 5:  # Skip noise
                    continue

                # Decision maker detection
                is_dm, title_found, company = _detect_decision_maker(title, desc)

                results.append({
                    "source": source,
                    "title": title[:300],
                    "content": desc[:800] if desc else title[:200],
                    "url": url_val,
                    "date": date_iso,
                    "relevance_score": round(score, 1),
                    "matched_keywords": ", ".join(keywords),
                    "tier": tier,
                    "category": category,
                    "is_decision_maker": is_dm,
                    "author_title": title_found if is_dm else "",
                    "author_company": company,
                })

        except Exception as e:
            print(f"  Google News parse error: {e}")
            continue

        time.sleep(1.5)  # Be polite

    # Deduplicate by URL or title
    seen = set()
    deduped = []
    for r in results:
        key = (r["title"][:100] + (r.get("url") or "")).lower()
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    deduped.sort(key=lambda x: x["relevance_score"], reverse=True)
    print(f"[Aggregator] Google News: {len(deduped)} articles (from {len(results)} raw, {len(search_queries)} queries)")
    return deduped[:max_results]


# ── Source 2: BioPharma/FierceBiotech RSS — Industry Feed ─────────────────────

def fetch_industry_rss(max_results: int = 30) -> list:
    """Fetch from FierceBiotech, Endpoints, BioPharma Dive RSS feeds."""
    feeds = [
        ("FierceBiotech", "https://www.fiercebiotech.com/rss/biotech"),
        ("Endpoints", "https://endpts.com/feed/"),
        ("BioPharma Dive", "https://www.biopharmadive.com/feeds/news/"),
    ]

    results = []
    for source_name, feed_url in feeds:
        resp = _safe_fetch(feed_url)
        if not resp:
            continue

        try:
            soup = BeautifulSoup(resp.text, "xml")
            items = soup.find_all("item") or soup.find_all("entry")

            for item in items[:20]:
                title_tag = item.find("title")
                title = title_tag.get_text(strip=True) if title_tag else ""
                if not title or len(title) < 10:
                    continue

                pub_tag = item.find("pubDate") or item.find("published") or item.find("updated")
                date_iso = _parse_rss_date(pub_tag.get_text(strip=True) if pub_tag else "")

                desc_tag = item.find("description") or item.find("summary")
                desc = ""
                if desc_tag:
                    raw = desc_tag.get_text(strip=True)
                    desc = BeautifulSoup(raw, "html.parser").get_text(strip=True)[:500]

                link_tag = item.find("link")
                url_val = ""
                if link_tag:
                    url_val = link_tag.get("href") or link_tag.get_text(strip=True)

                full_text = f"{title} {desc}"
                score, keywords, tier = _score_signal(full_text)
                is_dm, title_found, company = _detect_decision_maker(title, desc)

                results.append({
                    "source": source_name,
                    "title": title[:300],
                    "content": desc[:800] if desc else title[:200],
                    "url": url_val,
                    "date": date_iso,
                    "relevance_score": round(score, 1),
                    "matched_keywords": ", ".join(keywords),
                    "tier": tier,
                    "category": "industry_feed",
                    "is_decision_maker": is_dm,
                    "author_title": title_found if is_dm else "",
                    "author_company": company,
                })
        except Exception as e:
            print(f"  {source_name} parse error: {e}")
            continue

        time.sleep(1)

    # Deduplicate
    seen = set()
    deduped = []
    for r in results:
        key = r["title"][:100].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    deduped.sort(key=lambda x: x["relevance_score"], reverse=True)
    print(f"[Aggregator] Industry RSS: {len(deduped)} articles")
    return deduped[:max_results]


# ── Source 3: PR Newswire — Biotech Press Releases ────────────────────────────

def fetch_pr_newswire(max_results: int = 15) -> list:
    """Fetch biotech press releases from PR Newswire RSS."""
    url = "https://www.prnewswire.com/rss/biotechnology-latest-news/biotechnology-latest-news-list.rss"
    resp = _safe_fetch(url)
    if not resp:
        return []

    results = []
    try:
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")

        for item in items[:25]:
            title_tag = item.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""
            if not title:
                continue

            pub_tag = item.find("pubDate")
            date_iso = _parse_rss_date(pub_tag.get_text(strip=True) if pub_tag else "")

            desc_tag = item.find("description")
            desc = ""
            if desc_tag:
                raw = desc_tag.get_text(strip=True)
                desc = BeautifulSoup(raw, "html.parser").get_text(strip=True)[:500]

            link_tag = item.find("link")
            url_val = link_tag.get_text(strip=True) if link_tag else ""

            full_text = f"{title} {desc}"
            score, keywords, tier = _score_signal(full_text)
            is_dm, title_found, company = _detect_decision_maker(title, desc)

            results.append({
                "source": "PR Newswire",
                "title": title[:300],
                "content": desc[:800] if desc else title[:200],
                "url": url_val,
                "date": date_iso,
                "relevance_score": round(score, 1),
                "matched_keywords": ", ".join(keywords),
                "tier": tier,
                "category": "press_release",
                "is_decision_maker": is_dm,
                "author_title": title_found if is_dm else "",
                "author_company": company,
            })
    except Exception as e:
        print(f"  PR Newswire parse error: {e}")

    print(f"[Aggregator] PR Newswire: {len(results)} articles")
    return results[:max_results]


# ── Source 4: SEC EDGAR — Form D Filings (Funding Signals) ────────────────────

def fetch_sec_funding_signals(lookback_days: int = 90, max_results: int = 20) -> list:
    """Fetch recent biotech Form D filings as funding signals."""
    results = []
    since = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "q": '"biotech" OR "biopharmaceutical" OR "therapeutics" OR "biopharma" OR "pharmaceuticals"',
        "dateRange": "custom",
        "startdt": since,
        "enddt": today,
        "forms": "D",
    }
    headers = {"User-Agent": "MedicilonResearch/1.0"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  SEC EDGAR unavailable: {e}")
        return []

    hits = data.get("hits", {}).get("hits", [])
    seen = set()

    for hit in hits[:50]:
        try:
            src = hit.get("_source", {})
            names = src.get("display_names", [])
            if not names:
                continue

            raw_name = names[0]
            company_name = re.sub(r'\s*\(CIK.*?\)', '', raw_name).strip()
            skip_words = ['fund', 'lp', 'llc', 'partners', 'capital', 'ventures', 'management']
            if any(w in company_name.lower() for w in skip_words):
                continue
            if company_name in seen:
                continue
            seen.add(company_name)

            # Extract CIK: try ciks[] array first, then parse from display_names string
            ciks_list = src.get('ciks', [])
            cik = str(ciks_list[0]) if ciks_list else ''
            if not cik:
                m = re.search(r'CIK\s+(\d+)', raw_name)
                cik = m.group(1) if m else ''

            file_date = src.get("file_date", "")
            biz_loc = src.get("biz_locations", [""])[0]
            offering = src.get("total_offering_amount", 0) or 0
            amount_str = ""
            if offering > 0:
                if offering >= 1_000_000_000:
                    amount_str = f"${offering / 1e9:.1f}B"
                elif offering >= 1_000_000:
                    amount_str = f"${offering / 1e6:.0f}M"
                else:
                    amount_str = f"${offering / 1e3:.0f}K"

            content = f"{company_name} filed Form D"
            if amount_str:
                content += f" — offering up to {amount_str}"
            if biz_loc:
                content += f" — based in {biz_loc}"
            content += " (SEC EDGAR). Biotech company raising capital — potential CRO outsourcing opportunity for preclinical/clinical services."

            results.append({
                "source": "SEC EDGAR",
                "title": f"{company_name} Raises Capital — Form D Filing",
                "content": content[:800],
                "url": (
                    f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=D&dateb=&owner=include&count=10"
                    if cik else
                    f"https://www.sec.gov/cgi-bin/browse-edgar?company={company_name.replace(' ', '+')}&CIK=&type=D&dateb=&owner=include&count=10&search_text=&action=getcompany"
                ),
                "date": file_date or datetime.now().isoformat(),
                "relevance_score": 55.0,
                "matched_keywords": "funding, investment, biotech, preclinical",
                "tier": "A",
                "category": "funding_milestone",
                "is_decision_maker": False,
                "author_title": "",
                "author_company": company_name,
            })
        except Exception:
            continue

    print(f"[Aggregator] SEC EDGAR: {len(results)} Form D filings")
    return results[:max_results]


# ── Aggregation & Storage ─────────────────────────────────────────────────────

def aggregate_all(max_total: int = 100) -> list:
    """Run all sources and return merged, deduplicated, scored results."""
    all_results = []

    print("[Aggregator] Starting full intelligence aggregation...")
    print("=" * 50)

    # Run all sources
    all_results += fetch_google_news_biotech(40)
    all_results += fetch_industry_rss(30)
    all_results += fetch_pr_newswire(15)
    all_results += fetch_sec_funding_signals(90, 20)

    # Final dedup — aggressive title-based matching across sources
    seen = set()
    final = []
    for r in all_results:
        # Normalize title for dedup: remove special chars, lowercase, first 80 chars
        raw_title = (r.get("title", "") or "").strip()
        norm_title = re.sub(r'[^\w\s]', '', raw_title).lower().strip()
        dedup_key = norm_title[:80]  # First 80 chars of normalized title
        
        if dedup_key and dedup_key not in seen:
            seen.add(dedup_key)
            final.append(r)

    final.sort(key=lambda x: x["relevance_score"], reverse=True)
    final = final[:max_total]

    # Summary
    tiers = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    sources = {}
    dms = 0
    for r in final:
        tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
        sources[r["source"]] = sources.get(r["source"], 0) + 1
        if r.get("is_decision_maker"):
            dms += 1

    print(f"\n[Aggregator] Total: {len(final)} signals")
    print(f"  Tiers: S={tiers['S']}, A={tiers['A']}, B={tiers['B']}, C={tiers['C']}, D={tiers['D']}")
    print(f"  Decision-makers detected: {dms}")
    print(f"  Sources: {sources}")

    return final


def save_to_db(leads: list):
    """Save aggregated signals to the linkedin_posts table for scoring pipeline."""
    import sqlite3
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    inserted = 0
    for lead in leads:
        try:
            # Use title-only hash so same article from different sources deduplicates
            norm_title = re.sub(r'[^\w\s]', '', lead.get('title', '')[:80]).lower().strip()
            source_id = f"agg-{hash(norm_title)}"
            conn.execute("""
                INSERT OR IGNORE INTO linkedin_posts
                    (source_id, post_url, author_name, author_title, author_company,
                     content, post_date, relevance_score, matched_keywords, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source_id,
                lead.get("url", ""),
                lead.get("author_company", lead.get("source", "Industry Signal")),
                lead.get("author_title", ""),
                lead.get("author_company", ""),
                f"[{lead.get('source','')}] {lead.get('title','')}\n\n{lead.get('content','')[:600]}",
                lead.get("date", ""),
                lead.get("relevance_score", 0),
                lead.get("matched_keywords", ""),
                0,  # Not processed by scoring yet
            ))
            inserted += 1
        except Exception as e:
            print(f"  DB insert warning: {e}")
            continue

    conn.commit()

    # Also save decision-maker contacts
    dm_inserted = 0
    for lead in leads:
        if lead.get("is_decision_maker") and lead.get("author_company"):
            try:
                dm_id = f"dm-{hash(lead.get('author_company','') + lead.get('author_title',''))}"
                conn.execute("""
                    INSERT OR IGNORE INTO linkedin_contacts
                        (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    dm_id,
                    lead.get("author_company", "Unknown"),
                    lead.get("author_title", ""),
                    lead.get("author_company", ""),
                    "US",
                    lead.get("url", ""),
                    "3rd",
                    round(lead.get("relevance_score", 0) / 10, 1),
                ))
                dm_inserted += 1
            except Exception:
                continue

    conn.commit()
    conn.close()

    print(f"[Aggregator] DB: {inserted} posts inserted, {dm_inserted} contacts")
    return inserted, dm_inserted


def save_to_json(leads: list):
    """Also save to frontend/data for dashboard access."""
    out_path = BASE_DIR / "frontend" / "data" / "aggregated_intelligence.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "total": len(leads),
            "source": "multi-source_aggregation",
            "note": "No LinkedIn account required — public data aggregation",
        },
        "leads": leads,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"[Aggregator] JSON saved: {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LinkedIn Intelligence Aggregator — No LinkedIn needed")
    parser.add_argument("--max", type=int, default=100, help="Max results")
    parser.add_argument("--no-db", action="store_true", help="Skip database insert")
    parser.add_argument("--json-only", action="store_true", help="Only save JSON, no DB")
    args = parser.parse_args()

    if not HAS_DEPS:
        print("ERROR: pip install requests beautifulsoup4")
        exit(1)

    leads = aggregate_all(max_total=args.max)

    if not args.no_db:
        save_to_db(leads)
    if not args.json_only or args.no_db:
        save_to_json(leads)

    print("\nDone! No LinkedIn account was used.")
    print("Run this on a cron schedule for continuous BD intelligence.")
