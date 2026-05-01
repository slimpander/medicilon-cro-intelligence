#!/usr/bin/env python3
"""
CRO News Intelligence Fetcher
Fetches real news articles for CRO companies from the past 3 years.
Writes results to data/news_data.json for use by the frontend.

Usage:
    pip install requests beautifulsoup4
    python fetch_news.py

Optional (better results):
    Set NEWSAPI_KEY env var for NewsAPI.org results
    Set SERPAPI_KEY env var for Google News results
"""

import json
import os
import re
import time
from datetime import datetime, timedelta, date
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("WARNING: requests/beautifulsoup4 not installed.")
    print("Install with: pip install requests beautifulsoup4")

# ─── Configuration ────────────────────────────────────────────────────────────

# 3-year lookback window
LOOKBACK_YEARS = 3
CUTOFF_DATE = datetime.now() - timedelta(days=365 * LOOKBACK_YEARS)

# API keys (optional — set as environment variables)
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# CRO companies to track
CRO_COMPANIES = [
    "Charles River Laboratories",
    "Covance Labcorp",
    "WuXi AppTec",
    "Eurofins",
    "Pharmaron",
    "Crown Bioscience",
    "Syneos Health",
    "ICON plc",
    "BioAgilytix",
    "Altasciences",
    "Celerion",
    "Biotrial",
    "Medicilon",
]

# Short names for tagging (must match cro_data.json short_name values)
CRO_SHORT_NAMES = {
    "Charles River Laboratories": "Charles River",
    "Covance Labcorp": "Covance / Labcorp",
    "WuXi AppTec": "WuXi AppTec",
    "Eurofins": "Eurofins",
    "Pharmaron": "Pharmaron",
    "Crown Bioscience": "Crown Bioscience",
    "Syneos Health": "Syneos Health",
    "ICON plc": "ICON plc",
    "BioAgilytix": "BioAgilytix",
    "Altasciences": "Altasciences",
    "Celerion": "Celerion",
    "Biotrial": "Biotrial",
    "Medicilon": "Medicilon",
}

# Service keywords for auto-tagging articles
SERVICE_KEYWORDS = {
    "In Vivo / Mouse Services": ["in vivo", "mouse model", "xenograft", "pdx", "tumor model", "pharmacology model"],
    "DMPK": ["dmpk", "drug metabolism", "pharmacokinetics", "pk study", "metabolite", "clearance"],
    "ADME": ["adme", "absorption", "distribution", "metabolism", "excretion", "permeability", "caco-2"],
    "Toxicology": ["toxicology", "toxicity", "glp tox", "safety assessment", "genotoxicity"],
    "Bioanalysis": ["bioanalysis", "lc-ms", "immunoassay", "elisa", "bioanalytical", "mass spectrometry"],
    "CMC": ["cmc", "formulation", "drug substance", "drug product", "analytical chemistry", "stability"],
    "Clinical Trials": ["clinical trial", "phase i", "phase ii", "phase iii", "clinical study"],
    "Regulatory Affairs": ["regulatory", "fda submission", "ind filing", "nda", "bla"],
    "Biomarker / Genomics": ["biomarker", "genomics", "ngs", "sequencing", "omics"],
    "Protein Sciences / Biologics": ["biologics", "antibody", "protein expression", "biosimilar"],
}

US_STATE_ABBREVS = {
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
    "Wisconsin": "WI", "Wyoming": "WY",
}

STATE_SET = set(US_STATE_ABBREVS.values())

# ─── Helpers ──────────────────────────────────────────────────────────────────

def is_within_3_years(date_str: str) -> bool:
    """Return True if date_str (ISO format or partial) is within the 3-year window."""
    if not date_str:
        return True  # Unknown date: include by default
    try:
        # Handle ISO 8601 with or without time
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None) >= CUTOFF_DATE
    except Exception:
        pass
    # Try partial date strings: "2024-03", "2024", etc.
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            dt = datetime.strptime(date_str[:len(fmt.replace("%Y", "2024").replace("%m", "01").replace("%d", "01"))], fmt)
            return dt >= CUTOFF_DATE
        except Exception:
            continue
    return True  # Unparseable — include


def format_relative_date(date_str: str) -> str:
    """Convert ISO date string to relative label like '2d ago', '3w ago', '1y ago'."""
    if not date_str:
        return "unknown"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
        delta = datetime.now() - dt
        days = delta.days
        if days == 0:
            return "today"
        elif days == 1:
            return "1d ago"
        elif days < 7:
            return f"{days}d ago"
        elif days < 30:
            weeks = days // 7
            return f"{weeks}w ago"
        elif days < 365:
            months = days // 30
            return f"{months}mo ago"
        else:
            years = days // 365
            return f"{years}y ago"
    except Exception:
        return date_str[:10] if date_str else "unknown"


def extract_tags(title: str, summary: str, company_short: str) -> list:
    """Auto-extract tags: company name, US states, and service categories."""
    tags = [company_short]
    text = (title + " " + summary).lower()

    # Service tags
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tags.append(service)

    # State tags from full names
    combined = title + " " + summary
    for state_name, abbrev in US_STATE_ABBREVS.items():
        if state_name in combined:
            tags.append(abbrev)

    # State abbreviations (e.g. "Raleigh, NC")
    for match in re.finditer(r'\b([A-Z]{2})\b', combined):
        abbrev = match.group(1)
        if abbrev in STATE_SET:
            tags.append(abbrev)

    # Deduplicate preserving order
    seen = set()
    result = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


# ─── News Sources ─────────────────────────────────────────────────────────────

def fetch_newsapi(company: str, short_name: str) -> list:
    """Fetch from NewsAPI.org (requires free API key)."""
    if not NEWSAPI_KEY or not REQUESTS_AVAILABLE:
        return []

    from_date = CUTOFF_DATE.strftime("%Y-%m-%d")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": f'"{company}" CRO pharmaceutical',
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 20,
        "apiKey": NEWSAPI_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", [])
        results = []
        for a in articles:
            pub = a.get("publishedAt", "")
            if not is_within_3_years(pub):
                continue
            title = a.get("title", "").strip()
            summary = a.get("description", "").strip() or a.get("content", "").strip()
            source = a.get("source", {}).get("name", "NewsAPI")
            results.append({
                "title": title,
                "source": source,
                "date_iso": pub,
                "date": format_relative_date(pub),
                "url": a.get("url", ""),
                "summary": summary[:400] if summary else "",
                "tags": extract_tags(title, summary, short_name),
            })
        print(f"  NewsAPI: {len(results)} articles for {company}")
        return results
    except Exception as e:
        print(f"  NewsAPI error for {company}: {e}")
        return []


def fetch_google_news_rss(company: str, short_name: str) -> list:
    """Fetch from Google News RSS (no API key needed)."""
    if not REQUESTS_AVAILABLE:
        return []

    query = f"{company} CRO pharmaceutical drug development"
    encoded = requests.utils.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        results = []
        for item in items[:15]:
            title = item.find("title")
            title = title.get_text(strip=True) if title else ""
            pub_date = item.find("pubDate")
            pub_str = pub_date.get_text(strip=True) if pub_date else ""
            # Parse RFC 2822 date
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pub_str).replace(tzinfo=None)
                date_iso = dt.isoformat()
                if not is_within_3_years(date_iso):
                    continue
                date_label = format_relative_date(date_iso)
            except Exception:
                date_iso = ""
                date_label = pub_str[:10] if pub_str else "unknown"

            source_tag = item.find("source")
            source = source_tag.get_text(strip=True) if source_tag else "Google News"
            desc = item.find("description")
            summary = ""
            if desc:
                raw = desc.get_text(strip=True)
                # Google News descriptions often have HTML — strip it
                summary = BeautifulSoup(raw, "html.parser").get_text(strip=True)[:400]

            link = item.find("link")
            url_val = link.get_text(strip=True) if link else ""

            results.append({
                "title": title,
                "source": source,
                "date_iso": date_iso,
                "date": date_label,
                "url": url_val,
                "summary": summary,
                "tags": extract_tags(title, summary, short_name),
            })

        print(f"  Google News RSS: {len(results)} articles for {company}")
        return results
    except Exception as e:
        print(f"  Google News RSS error for {company}: {e}")
        return []


def fetch_bing_news(company: str, short_name: str) -> list:
    """Fallback: scrape Bing News search results."""
    if not REQUESTS_AVAILABLE:
        return []

    query = f"{company} CRO pharmaceutical expansion acquisition"
    encoded = requests.utils.quote(query)
    url = f"https://www.bing.com/news/search?q={encoded}&format=RSS"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        results = []
        for item in items[:10]:
            title_tag = item.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""
            pub_tag = item.find("pubDate")
            pub_str = pub_tag.get_text(strip=True) if pub_tag else ""
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pub_str).replace(tzinfo=None)
                date_iso = dt.isoformat()
                if not is_within_3_years(date_iso):
                    continue
                date_label = format_relative_date(date_iso)
            except Exception:
                date_iso = ""
                date_label = "unknown"

            desc_tag = item.find("description")
            summary = ""
            if desc_tag:
                summary = BeautifulSoup(desc_tag.get_text(), "html.parser").get_text(strip=True)[:400]

            link_tag = item.find("link")
            url_val = link_tag.get_text(strip=True) if link_tag else ""
            source_tag = item.find("source")
            source = source_tag.get_text(strip=True) if source_tag else "Bing News"

            results.append({
                "title": title,
                "source": source,
                "date_iso": date_iso,
                "date": date_label,
                "url": url_val,
                "summary": summary,
                "tags": extract_tags(title, summary, short_name),
            })
        print(f"  Bing News RSS: {len(results)} articles for {company}")
        return results
    except Exception as e:
        print(f"  Bing News error for {company}: {e}")
        return []


# ─── GDELT Fetcher ──────────────────────────────────────────────────────────────

def gdelt_query_chunks(start_dt: datetime, end_dt: datetime, chunk_months: int = 3) -> list:
    """Split a date range into chunks for GDELT queries (max 3-month window per call)."""
    chunks = []
    current = start_dt
    while current < end_dt:
        chunk_end = min(current + timedelta(days=chunk_months * 30), end_dt)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    return chunks


# GDELT query terms per company
GDELT_QUERIES = {
    "Charles River Laboratories": '"Charles River" laboratory pharmaceutical',
    "Covance Labcorp": '"Covance" OR "Labcorp Drug Development" CRO',
    "WuXi AppTec": '"WuXi AppTec" pharmaceutical',
    "Eurofins": '"Eurofins" pharmaceutical laboratory',
    "Pharmaron": '"Pharmaron" CRO pharmaceutical',
    "Crown Bioscience": '"Crown Bioscience" oncology',
    "Syneos Health": '"Syneos Health" clinical',
    "ICON plc": '"ICON plc" CRO clinical',
    "BioAgilytix": '"BioAgilytix" bioanalysis',
    "Altasciences": '"Altasciences" CRO',
    "Celerion": '"Celerion" clinical pharmacology',
    "Biotrial": '"Biotrial" clinical',
    "Medicilon": '"Medicilon" CRO pharmaceutical',
}


def fetch_gdelt_all_companies(max_per_chunk: int = 25) -> list:
    """Fetch GDELT for ALL companies in one pass — one request per 6-month chunk.
    
    Combines all company queries with OR so we only make ~10 requests total
    instead of 10 per company. Much friendlier to GDELT rate limits.
    Note: GDELT free API rate-limits heavily on historical queries.
    If you get many 429s, use --no-gdelt and rely on RSS + PR Newswire instead.
    """
    if not REQUESTS_AVAILABLE:
        return []

    # Build one big OR query covering all companies
    company_terms = list(GDELT_QUERIES.values())
    # GDELT supports long queries; group into batches if needed
    combined_query = " OR ".join(f"({t})" for t in company_terms)

    chunks = gdelt_query_chunks(CUTOFF_DATE, datetime.now(), chunk_months=6)
    all_results = []
    seen_urls = set()

    print(f"  GDELT: querying {len(chunks)} chunks (6-month windows) for all companies...")

    for chunk_idx, (chunk_start, chunk_end) in enumerate(chunks, 1):
        start_str = chunk_start.strftime("%Y%m%d%H%M%S")
        end_str = chunk_end.strftime("%Y%m%d%H%M%S")
        print(f"    Chunk {chunk_idx}/{len(chunks)}: {chunk_start.strftime('%Y-%m')} to {chunk_end.strftime('%Y-%m')}")

        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": combined_query,
            "mode": "artlist",
            "maxrecords": max_per_chunk,
            "format": "json",
            "startdatetime": start_str,
            "enddatetime": end_str,
            "sort": "DateDesc",
            "sourcelang": "english",
        }

        retries = 3
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, timeout=25)
                if resp.status_code == 429:
                    wait = 15 * (attempt + 1)
                    print(f"    429 rate limit, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                articles = data.get("articles") or []

                chunk_new = 0
                for a in articles:
                    art_url = a.get("url", "")
                    if art_url in seen_urls:
                        continue
                    seen_urls.add(art_url)

                    title = a.get("title", "").strip()
                    if not title:
                        continue

                    # Match to company by keyword
                    matched_company = None
                    matched_short = None
                    title_lower = title.lower()
                    for comp, short in CRO_SHORT_NAMES.items():
                        kw = short.lower().split()[0]  # first word of short name
                        if kw in title_lower:
                            matched_company = comp
                            matched_short = short
                            break

                    if not matched_short:
                        continue  # Skip articles that don't clearly mention a tracked CRO

                    seen_date = a.get("seendate", "")
                    try:
                        dt = datetime.strptime(seen_date, "%Y%m%dT%H%M%SZ")
                        date_iso = dt.isoformat()
                        date_label = format_relative_date(date_iso)
                    except Exception:
                        date_iso = ""
                        date_label = "unknown"

                    source = a.get("domain", "GDELT")

                    all_results.append({
                        "title": title,
                        "source": source,
                        "date_iso": date_iso,
                        "date": date_label,
                        "url": art_url,
                        "summary": "",
                        "tags": extract_tags(title, "", matched_short),
                    })
                    chunk_new += 1

                print(f"    -> {chunk_new} new articles")
                break  # success

            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(8)
                else:
                    print(f"    Chunk {chunk_idx} failed: {type(e).__name__}: {e}")

        time.sleep(6)  # 6s between chunks

    print(f"  GDELT total: {len(all_results)} articles across {len(chunks)} chunks")
    return all_results


def fetch_gdelt(company: str, short_name: str, max_per_chunk: int = 10) -> list:
    """Per-company GDELT stub — actual fetching done in fetch_gdelt_all_companies()."""
    return []  # Handled in batch mode


def _placeholder_gdelt(company: str, short_name: str, max_per_chunk: int = 10) -> list:
    """Original per-company GDELT fetch (kept for reference, not used in batch mode)."""
    if not REQUESTS_AVAILABLE:
        return []
    query = GDELT_QUERIES.get(company, f'"{company}" CRO pharmaceutical')
    chunks = gdelt_query_chunks(CUTOFF_DATE, datetime.now(), chunk_months=6)
    all_results = []
    seen_urls = set()

    for chunk_start, chunk_end in chunks:
        start_str = chunk_start.strftime("%Y%m%d%H%M%S")
        end_str = chunk_end.strftime("%Y%m%d%H%M%S")

        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": max_per_chunk,
            "format": "json",
            "startdatetime": start_str,
            "enddatetime": end_str,
            "sort": "DateDesc",
            "sourcelang": "english",
        }

        retries = 3
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, timeout=25)
                if resp.status_code == 429:
                    wait = 10 * (attempt + 1)  # 10s, 20s, 30s backoff
                    print(f"  GDELT 429 rate limit, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                articles = data.get("articles") or []

                for a in articles:
                    art_url = a.get("url", "")
                    if art_url in seen_urls:
                        continue
                    seen_urls.add(art_url)

                    title = a.get("title", "").strip()
                    if not title:
                        continue

                    # Parse GDELT date: "20231003T114500Z"
                    seen_date = a.get("seendate", "")
                    try:
                        dt = datetime.strptime(seen_date, "%Y%m%dT%H%M%SZ")
                        date_iso = dt.isoformat()
                        date_label = format_relative_date(date_iso)
                    except Exception:
                        date_iso = ""
                        date_label = "unknown"

                    source = a.get("domain", "GDELT")
                    summary = ""  # GDELT artlist doesn't include body text

                    all_results.append({
                        "title": title,
                        "source": source,
                        "date_iso": date_iso,
                        "date": date_label,
                        "url": art_url,
                        "summary": summary,
                        "tags": extract_tags(title, summary, short_name),
                    })
                break  # success

            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(8)
                else:
                    print(f"  GDELT chunk failed ({start_str[:8]}-{end_str[:8]}): {type(e).__name__}")

        time.sleep(5)  # 5s between every GDELT chunk to respect rate limits

    print(f"  GDELT: {len(all_results)} articles for {company} across {len(chunks)} chunks")
    return all_results


# ─── PR Newswire / GlobeNewsWire RSS ──────────────────────────────────────

# Press release RSS feeds per company (official/semi-official sources)
PR_RSS_FEEDS = {
    "Charles River": [
        "https://www.prnewswire.com/rss/news-releases-list.rss?company=charles-river-laboratories",
        "https://www.globenewswire.com/RssFeed/organization/charles-river-laboratories-international-inc",
    ],
    "WuXi AppTec": [
        "https://www.prnewswire.com/rss/news-releases-list.rss?company=wuxi-apptec",
        "https://www.globenewswire.com/RssFeed/organization/wuxi-apptec",
    ],
    "Eurofins": [
        "https://www.globenewswire.com/RssFeed/organization/eurofins-scientific",
    ],
    "Pharmaron": [
        "https://www.prnewswire.com/rss/news-releases-list.rss?company=pharmaron",
    ],
    "Crown Bioscience": [
        "https://www.prnewswire.com/rss/news-releases-list.rss?company=crown-bioscience",
    ],
    "Syneos Health": [
        "https://www.prnewswire.com/rss/news-releases-list.rss?company=syneos-health",
        "https://www.globenewswire.com/RssFeed/organization/syneos-health",
    ],
    "ICON plc": [
        "https://www.globenewswire.com/RssFeed/organization/icon-plc",
        "https://www.prnewswire.com/rss/news-releases-list.rss?company=icon-plc",
    ],
    "Medicilon": [
        "https://www.prnewswire.com/rss/news-releases-list.rss?company=medicilon",
    ],
    "Covance / Labcorp": [
        "https://www.globenewswire.com/RssFeed/organization/labcorp",
    ],
    "BioAgilytix": [
        "https://www.prnewswire.com/rss/news-releases-list.rss?company=bioagilytix",
    ],
    "Altasciences": [
        "https://www.prnewswire.com/rss/news-releases-list.rss?company=altasciences",
    ],
}


def fetch_pr_feeds(short_name: str) -> list:
    """Fetch company press releases from PR Newswire / GlobeNewsWire RSS.
    No rate limits, covers several years of press releases.
    """
    if not REQUESTS_AVAILABLE:
        return []

    feeds = PR_RSS_FEEDS.get(short_name, [])
    if not feeds:
        return []

    results = []
    seen_urls = set()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for feed_url in feeds:
        try:
            resp = requests.get(feed_url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "xml")
            items = soup.find_all("item")

            for item in items:
                link_tag = item.find("link")
                url_val = link_tag.get_text(strip=True) if link_tag else ""
                if url_val in seen_urls:
                    continue
                seen_urls.add(url_val)

                title_tag = item.find("title")
                title = title_tag.get_text(strip=True) if title_tag else ""
                if not title:
                    continue

                pub_tag = item.find("pubDate")
                pub_str = pub_tag.get_text(strip=True) if pub_tag else ""
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub_str).replace(tzinfo=None)
                    date_iso = dt.isoformat()
                    if not is_within_3_years(date_iso):
                        continue
                    date_label = format_relative_date(date_iso)
                except Exception:
                    date_iso = ""
                    date_label = "unknown"

                desc_tag = item.find("description")
                summary = ""
                if desc_tag:
                    summary = BeautifulSoup(desc_tag.get_text(), "html.parser").get_text(strip=True)[:400]

                domain = "prnewswire.com" if "prnewswire" in feed_url else "globenewswire.com"

                results.append({
                    "title": title,
                    "source": domain,
                    "date_iso": date_iso,
                    "date": date_label,
                    "url": url_val,
                    "summary": summary,
                    "tags": extract_tags(title, summary, short_name),
                })

            time.sleep(0.5)
        except Exception as e:
            print(f"  PR feed error ({feed_url[:50]}...): {type(e).__name__}")

    print(f"  PR Newswire/GlobeNewsWire: {len(results)} press releases for {short_name}")
    return results


# ─── Deduplication ────────────────────────────────────────────────────────────

def deduplicate(articles: list) -> list:
    """Remove duplicate articles by title similarity."""
    seen_titles = {}
    result = []
    for a in articles:
        # Normalize title for comparison
        key = re.sub(r'\W+', ' ', a["title"].lower()).strip()[:80]
        if key not in seen_titles:
            seen_titles[key] = True
            result.append(a)
    return result


# ─── Main Fetch ───────────────────────────────────────────────────────────────

def fetch_all_news() -> list:
    """Fetch news for all CRO companies and return deduplicated, date-filtered list."""
    all_articles = []
    total_companies = len(CRO_COMPANIES)

    # ── GDELT batch fetch (opt-in, all companies in one pass) ───────────────
    # GDELT free API rate-limits heavily; enabled via --gdelt flag
    if os.getenv("USE_GDELT"):
        print("\nFetching GDELT historical archive (all companies, batch mode)...")
        gdelt_all = fetch_gdelt_all_companies()
        all_articles.extend(gdelt_all)
        print(f"GDELT batch complete: {len(gdelt_all)} articles")

    # ── Per-company: NewsAPI + Google RSS + PR feeds ───────────────────────
    for i, company in enumerate(CRO_COMPANIES, 1):
        short_name = CRO_SHORT_NAMES.get(company, company)
        print(f"\n[{i}/{total_companies}] Fetching: {company}")

        articles = []

        # 1. NewsAPI (best quality, requires key)
        if NEWSAPI_KEY:
            articles = fetch_newsapi(company, short_name)

        # 2. Google News RSS (free, good for recent ~12 months)
        rss_articles = fetch_google_news_rss(company, short_name)
        time.sleep(1)

        # 3. PR Newswire / GlobeNewsWire (official press releases, multi-year)
        pr_articles = fetch_pr_feeds(short_name)
        time.sleep(0.5)

        combined = articles + rss_articles + pr_articles

        # Apply lookback filter
        filtered = [a for a in combined if is_within_3_years(a.get("date_iso", ""))]
        skipped = len(combined) - len(filtered)
        if skipped:
            print(f"  Filtered out {skipped} articles outside lookback window")

        all_articles.extend(filtered)
        time.sleep(1)

    # Deduplicate across all companies
    before = len(all_articles)
    all_articles = deduplicate(all_articles)
    print(f"\nDeduplication: {before} -> {len(all_articles)} articles")

    # Sort by date (newest first)
    all_articles.sort(key=lambda a: a.get("date_iso", ""), reverse=True)

    # Assign sequential IDs
    for i, a in enumerate(all_articles, 1):
        a["id"] = i

    return all_articles


def save_news(articles: list, path: str = "data/news_data.json") -> None:
    """Save fetched news to JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    output = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "cutoff_date": CUTOFF_DATE.strftime("%Y-%m-%d"),
            "lookback_years": LOOKBACK_YEARS,
            "total_articles": len(articles),
            "source": "live_fetch",
        },
        "articles": articles,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(articles)} articles to {path}")


def print_summary(articles: list) -> None:
    """Print fetch summary."""
    print("\n" + "=" * 60)
    print("NEWS FETCH SUMMARY")
    print("=" * 60)
    print(f"Total articles: {len(articles)}")
    print(f"Date range: past {LOOKBACK_YEARS} years (since {CUTOFF_DATE.strftime('%Y-%m-%d')})")

    # By company
    company_counts = {}
    for a in articles:
        for tag in a.get("tags", []):
            if tag in CRO_SHORT_NAMES.values():
                company_counts[tag] = company_counts.get(tag, 0) + 1
    print("\nBy company:")
    for company, count in sorted(company_counts.items(), key=lambda x: -x[1]):
        print(f"  {company}: {count}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CRO News Intelligence Fetcher")
    parser.add_argument("--output", default="data/news_data.json", help="Output JSON path")
    parser.add_argument("--years", type=int, default=3, help="Lookback window in years (default: 3, max useful: 8)")
    parser.add_argument("--gdelt", action="store_true", help="Include GDELT historical archive (slower, may hit rate limits)")
    args = parser.parse_args()

    # Override if custom years specified
    if args.years != LOOKBACK_YEARS:
        LOOKBACK_YEARS = args.years
        CUTOFF_DATE = datetime.now() - timedelta(days=365 * LOOKBACK_YEARS)

    print("CRO News Intelligence Fetcher")
    print(f"Lookback: {LOOKBACK_YEARS} years (since {CUTOFF_DATE.strftime('%Y-%m-%d')})")
    print("=" * 60)

    if not NEWSAPI_KEY:
        print("TIP: Set NEWSAPI_KEY env var for better results (free at newsapi.org)")
    if not REQUESTS_AVAILABLE:
        print("ERROR: Install dependencies first: pip install requests beautifulsoup4")
        exit(1)

    if args.gdelt:
        os.environ["USE_GDELT"] = "1"
        print("GDELT enabled (--gdelt flag)")

    articles = fetch_all_news()
    print_summary(articles)
    save_news(articles, args.output)

    print("\nDone! Next step: update index.html to load from data/news_data.json")
    print("Run: python patch_news_live.py")
