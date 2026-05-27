"""
News Fetcher Service — CRO & Biotech News via RSS + optional NewsAPI
Consolidated from cro-map/fetch_news.py. Runs in-process, no subprocess needed.
"""
import json
import os
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

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DATA = BASE_DIR / "frontend" / "data"
OUTPUT_PATH = FRONTEND_DATA / "news_data.json"
LOOKBACK_DAYS = 365  # 1 year

# CRO companies to track
CRO_COMPANIES = [
    "Charles River Laboratories", "Labcorp", "WuXi AppTec",
    "Eurofins Scientific", "Pharmaron", "ICON plc",
    "Syneos Health", "Medicilon", "Altasciences",
]

# Biotech news sources for PitchBook-style feed
BIOTECH_NEWS_SOURCES = [
    {
        "name": "FierceBiotech",
        "url": "https://www.fiercebiotech.com/rss/biotech",
        "type": "rss",
    },
    {
        "name": "Endpoints News",
        "url": "https://endpts.com/feed/",
        "type": "rss",
    },
    {
        "name": "BioPharma Dive",
        "url": "https://www.biopharmadive.com/feeds/news/",
        "type": "rss",
    },
]

SERVICE_KEYWORDS = {
    "In Vivo / Mouse Services": ["in vivo", "mouse model", "xenograft", "pdx", "tumor model"],
    "DMPK": ["dmpk", "drug metabolism", "pharmacokinetics", "pk study"],
    "ADME": ["adme", "absorption", "distribution", "metabolism"],
    "Toxicology": ["toxicology", "toxicity", "safety assessment", "genotoxicity"],
    "Bioanalysis": ["bioanalysis", "lc-ms", "immunoassay", "bioanalytical"],
    "CMC": ["cmc", "formulation", "drug substance", "drug product"],
    "Clinical Trials": ["clinical trial", "phase i", "phase ii", "phase iii"],
    "Biologics": ["biologics", "antibody", "protein expression", "biosimilar"],
}

DEAL_KEYWORDS = [
    "acquired", "acquisition", "merger", "merges", "buyout",
    "raised", "raises", "funding", "series a", "series b", "series c",
    "series d", "ipo", "public offering", "private equity",
    "venture capital", "seed round", "financing round", "investment",
    "partnership", "collaboration", "licensing deal", "strategic alliance",
    "spinout", "spin-off", "divestiture", "restructuring",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_get(url, timeout=15, retries=2):
    if not HAS_DEPS:
        return None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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


def parse_rss_date(pub_str: str) -> Optional[str]:
    """Parse RSS pubDate to ISO format."""
    if not pub_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_str).replace(tzinfo=None)
        return dt.isoformat()
    except Exception:
        pass
    # Try simple date formats
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(pub_str, fmt).isoformat()
        except Exception:
            continue
    return pub_str[:10] if pub_str else None


def extract_tags(title: str, summary: str, company: str = "") -> list:
    """Auto-extract service tags from article text."""
    tags = [company] if company else []
    text = (title + " " + summary).lower()
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tags.append(service)
    # Deduplicate
    seen = set()
    result = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def extract_deal_info(title: str, summary: str) -> Optional[dict]:
    """Try to extract deal information from article text."""
    text = (title + " " + summary).lower()

    # Check if it's a deal-related article
    if not any(kw in text for kw in DEAL_KEYWORDS):
        return None

    # Try to extract amounts (e.g., "$1.2B", "$180 million", "$500M")
    amount_patterns = [
        r'\$(\d+(?:\.\d+)?)\s*(billion|B|million|M)',
        r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(billion|million)',
    ]
    amount = None
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num = float(match.group(1).replace(",", ""))
            unit = match.group(2).lower()
            if unit in ("billion", "b"):
                amount = num * 1_000_000_000
            elif unit in ("million", "m"):
                amount = num * 1_000_000
            break

    # Determine deal type
    deal_type = "News"
    if any(kw in text for kw in ["acquired", "acquisition", "merger", "merges", "buyout"]):
        deal_type = "M&A"
    elif any(kw in text for kw in ["ipo", "public offering"]):
        deal_type = "IPO"
    elif any(kw in text for kw in ["series a", "seed round"]):
        deal_type = "Series A"
    elif "series b" in text:
        deal_type = "Series B"
    elif "series c" in text:
        deal_type = "Series C"
    elif "series d" in text or "series e" in text:
        deal_type = "Series D+"
    elif any(kw in text for kw in ["private equity", "growth equity"]):
        deal_type = "Private Equity"
    elif any(kw in text for kw in ["raised", "raises", "funding", "financing", "investment"]):
        deal_type = "Funding"

    return {
        "deal_type": deal_type,
        "amount": amount,
    }


# ── RSS Feed Fetcher ──────────────────────────────────────────────────────────

def fetch_rss_feed(url: str, source_name: str, limit: int = 20) -> list:
    """Fetch and parse an RSS/Atom feed."""
    if not HAS_DEPS:
        return []

    resp = safe_get(url)
    if not resp:
        print(f"  RSS fetch failed: {url}")
        return []

    try:
        # Try XML parsing first
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")

        # If no items found, try Atom format
        if not items:
            items = soup.find_all("entry")

        results = []
        for item in items[:limit]:
            # Title
            title_tag = item.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Link
            link_tag = item.find("link")
            if link_tag:
                url_val = link_tag.get("href") or link_tag.get_text(strip=True)
            else:
                url_val = ""

            # Date
            pub_tag = item.find("pubDate") or item.find("published") or item.find("updated")
            pub_str = pub_tag.get_text(strip=True) if pub_tag else ""
            date_iso = parse_rss_date(pub_str)

            # Summary/description
            desc_tag = item.find("description") or item.find("summary") or item.find("content")
            summary = ""
            if desc_tag:
                raw = desc_tag.get_text(strip=True)
                summary = BeautifulSoup(raw, "html.parser").get_text(strip=True)[:400]

            if not title:
                continue

            # Extract deal info
            deal_info = extract_deal_info(title, summary)

            results.append({
                "title": title.strip(),
                "source": source_name,
                "date_iso": date_iso or datetime.now().isoformat(),
                "date": _format_relative(date_iso) if date_iso else "unknown",
                "url": url_val,
                "summary": summary,
                "tags": extract_tags(title, summary, source_name),
                "is_deal": bool(deal_info),
                "deal_type": deal_info.get("deal_type") if deal_info else None,
                "deal_amount": deal_info.get("amount") if deal_info else None,
            })

        print(f"  {source_name}: {len(results)} articles")
        return results

    except Exception as e:
        print(f"  RSS parse error ({source_name}): {e}")
        return []


def fetch_cro_news_rss(company: str) -> list:
    """Fetch news for a specific CRO company via Google News RSS."""
    if not HAS_DEPS:
        return []

    query = f'"{company}" CRO pharmaceutical'
    encoded = requests.utils.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

    return fetch_rss_feed(url, f"Google News - {company}", limit=10)


# ── Fetch All News ────────────────────────────────────────────────────────────

def fetch_all_news(use_gdelt: bool = False) -> list:
    """Fetch news from all sources and return deduplicated list."""
    all_articles = []

    # 1. Biotech news RSS feeds (FierceBiotech, Endpoints, BioPharma Dive)
    print("[NewsFetcher] Fetching biotech RSS feeds...")
    for source in BIOTECH_NEWS_SOURCES:
        articles = fetch_rss_feed(source["url"], source["name"], limit=15)
        all_articles.extend(articles)
        time.sleep(1)  # Be polite to servers

    # 2. CRO company news via Google News RSS (more limited to avoid rate limits)
    print("[NewsFetcher] Fetching CRO company news...")
    for company in CRO_COMPANIES[:5]:  # Top 5 to keep it fast
        articles = fetch_cro_news_rss(company)
        all_articles.extend(articles)
        time.sleep(1.5)

    # 3. Optional: GDELT (very slow, opt-in)
    if use_gdelt:
        print("[NewsFetcher] GDELT skipped — use --gdelt flag for historical data")

    # Deduplicate by title
    seen = set()
    deduped = []
    for a in all_articles:
        key = re.sub(r'\W+', ' ', a.get("title", "").lower())[:80]
        if key and key not in seen:
            seen.add(key)
            deduped.append(a)

    # Sort by date, newest first
    deduped.sort(key=lambda a: a.get("date_iso", ""), reverse=True)

    # Assign IDs
    for i, a in enumerate(deduped, 1):
        a["id"] = i

    print(f"[NewsFetcher] Total: {len(deduped)} articles (from {len(all_articles)} raw)")

    return deduped


def fetch_biotech_deals(limit: int = 15) -> list:
    """Fetch recent biotech deals from RSS feeds — used for PitchBook feed."""
    all_articles = []

    for source in BIOTECH_NEWS_SOURCES:
        articles = fetch_rss_feed(source["url"], source["name"], limit=10)
        all_articles.extend(articles)
        time.sleep(1)

    # Filter to only deal-related articles
    deals = [a for a in all_articles if a.get("is_deal") and a.get("deal_type")]

    # Deduplicate
    seen = set()
    deduped = []
    for d in deals:
        key = re.sub(r'\W+', ' ', d.get("title", "").lower())[:60]
        if key and key not in seen:
            seen.add(key)
            deduped.append(d)

    return deduped[:limit]


# ── Save ──────────────────────────────────────────────────────────────────────

def _format_relative(date_iso: str) -> str:
    if not date_iso:
        return "unknown"
    try:
        dt = datetime.fromisoformat(date_iso.replace("Z", "+00:00")).replace(tzinfo=None)
        delta = datetime.now() - dt
        days = delta.days
        if days == 0: return "today"
        if days < 7: return f"{days}d ago"
        if days < 30: return f"{days // 7}w ago"
        if days < 365: return f"{days // 30}mo ago"
        return f"{days // 365}y ago"
    except Exception:
        return date_iso[:10]


def save_news(articles: list) -> dict:
    """Save articles to frontend data directory."""
    FRONTEND_DATA.mkdir(parents=True, exist_ok=True)
    out = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "total_articles": len(articles),
            "source": "live_rss_fetch",
        },
        "articles": articles,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return {"ok": True, "count": len(articles), "path": str(OUTPUT_PATH)}


def save_deals(deals: list) -> dict:
    """Save biotech deals for PitchBook-style display."""
    path = FRONTEND_DATA / "deals.json"
    FRONTEND_DATA.mkdir(parents=True, exist_ok=True)
    out = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "total": len(deals),
            "source": "live_rss_scrape",
        },
        "deals": [
            {
                "deal_type": d.get("deal_type"),
                "target": d.get("title", "")[:100],
                "amount": _fmt_amount(d.get("deal_amount")),
                "amount_usd": d.get("deal_amount"),
                "date": d.get("date_iso", "")[:10],
                "description": d.get("summary", "")[:200],
                "url": d.get("url", ""),
                "source": d.get("source", ""),
            }
            for d in deals
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return {"ok": True, "count": len(deals), "path": str(path)}


def _fmt_amount(amount):
    if not amount:
        return ""
    if amount >= 1_000_000_000:
        return f"${amount / 1e9:.1f}B"
    if amount >= 1_000_000:
        return f"${amount / 1e6:.0f}M"
    return f"${amount / 1e3:.0f}K"


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="News Fetcher — CRO & biotech RSS")
    parser.add_argument("--gdelt", action="store_true", help="Include GDELT (slow)")
    parser.add_argument("--deals-only", action="store_true", help="Only fetch biotech deals")
    args = parser.parse_args()

    if args.deals_only:
        print("Fetching biotech deals...")
        deals = fetch_biotech_deals(limit=20)
        result = save_deals(deals)
        print(f"Saved {result['count']} deals to {result['path']}")
    else:
        print("Fetching all CRO/biotech news...")
        articles = fetch_all_news(use_gdelt=args.gdelt)
        result = save_news(articles)
        print(f"Saved {result['count']} articles to {result['path']}")

        # Also fetch deals
        deals = fetch_biotech_deals(limit=15)
        save_deals(deals)
        print(f"Also saved {len(deals)} deal articles")
