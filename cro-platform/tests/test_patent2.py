import httpx
r = httpx.get('http://localhost:8000/api/patents/search?q=DMPK+preclinical&limit=3', timeout=20)
data = r.json()
print(f"Total: {data['total']}")
print(f"Source: {data['source']}")
for p in data['results']:
    print(f"  {p.get('patent_number','?')} — {p.get('title','')[:80]}")
    print(f"    {p.get('assignee','')}  |  {p.get('date','')}")
