import httpx

# Test Lens.org API
url = "https://api.lens.org/scholarly/search"
r = httpx.post(url, json={
    "query": {
        "bool": {
            "must": [
                {"term": {"publication_type": "patent"}},
                {"query_string": {"query": "DMPK preclinical", "fields": ["title", "abstract"]}},
            ]
        }
    },
    "size": 3,
    "from": 0,
    "sort": [{"date_published": "desc"}],
    "include": ["lens_id", "title", "date_published", "applicants", "abstract"],
}, headers={
    "Content-Type": "application/json",
    "User-Agent": "Medicilon-CRO-Intelligence/1.0",
}, timeout=15, follow_redirects=True)

print("Status:", r.status_code)
if r.status_code == 200:
    data = r.json()
    print("Keys:", list(data.keys()))
    hits = data.get("data", [])
    print(f"Hits: {len(hits)}")
    for h in hits[:3]:
        title = h.get("title", "?")
        lid = h.get("lens_id", "?")
        applicants = h.get("applicants", [])
        name = applicants[0].get("name", "") if applicants else ""
        print(f"  {lid} — {title[:80]}")
        print(f"    {name} | {h.get('date_published','')}")
else:
    print("Body:", r.text[:500])
