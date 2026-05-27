"""
Patent Search Service — Backend proxy for patent searching
Primary: Local curated patent database (instant results)
Fallback: The Lens API / Google Patents external search
"""
import json
import os
from pathlib import Path
from typing import Optional


def search_patents(query: str, limit: int = 8) -> dict:
    """
    Search patents from local curated database, with fallback to external search.
    Returns inline results with patent details.
    """
    # 1. Local curated database
    results = _search_local(query, limit)

    # 2. If local results are sparse, add external search option
    if len(results) < 3:
        q_encoded = query.replace(' ', '+')
        results.append({
            "patent_number": "Search",
            "title": f"Search \"{query}\" on Google Patents",
            "date": "",
            "assignee": "External Search",
            "abstract": f"Expand search to full patent database",
            "url": f"https://patents.google.com/?q={q_encoded}",
            "is_external": True,
        })

    return {
        "total": len(results) if results else 0,
        "results": results,
        "query": query,
        "source": "curated + google_patents",
    }


def _search_local(query: str, limit: int) -> list:
    """Search local curated patent database."""
    patent_file = Path(__file__).resolve().parent.parent.parent / "frontend" / "data" / "patents.json"
    if not patent_file.exists():
        return []

    with open(patent_file, 'r', encoding='utf-8') as f:
        patents = json.load(f)

    q_lower = query.lower()
    scored = []

    for p in patents:
        score = 0
        title = (p.get("title", "") or "").lower()
        abstract = (p.get("abstract", "") or "").lower()
        assignee = (p.get("assignee", "") or "").lower()
        tags = [t.lower() for t in p.get("tags", [])]

        # Title match (highest weight)
        if q_lower in title:
            score += 10
        # Individual word matches
        for word in q_lower.split():
            if len(word) > 2:
                if word in title:
                    score += 5
                if word in abstract:
                    score += 3
                if word in assignee:
                    score += 2
                if any(word in tag for tag in tags):
                    score += 4

        if score > 0:
            scored.append((score, p))

    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:limit]]


# Legacy functions kept for direct API use
def _try_lens_org(query: str, limit: int) -> list:
    """Try The Lens API (requires auth key). Kept for future use."""
    return []
