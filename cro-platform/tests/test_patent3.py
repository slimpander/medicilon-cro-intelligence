"""Test Google Patents scraping."""
import httpx
import re

query = "DMPK+preclinical"
url = f"https://patents.google.com/?q={query}&num=5"
r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=15, follow_redirects=True)
html = r.text
print(f"Status: {r.status_code}, Length: {len(html)}")

# Look for patent results in the page HTML
# Google Patents renders results as search-result items
patents = re.findall(r'<a[^>]*href="/patent/([A-Z]{2}\d+)/[^"]*"[^>]*>(.*?)</a>', html)
print(f"\nFound {len(patents)} patent links:")
for num, rest in patents[:5]:
    # Try to find title near the link
    title = re.sub(r'<[^>]+>', '', rest).strip()[:100]
    print(f"  {num} — {title}")

# Also look for result-item divs
results = re.findall(r'class="[^"]*result[^"]*"[^>]*>(.*?)</(?:div|article)>', html, re.DOTALL)
print(f"\nResult divs: {len(results)}")
for r_div in results[:2]:
    clean = re.sub(r'<[^>]+>', ' ', r_div)
    clean = re.sub(r'\s+', ' ', clean).strip()[:200]
    print(f"  {clean}")

# Check for meta or structured data
if 'search-result' in html:
    print("\nFound search-result class!")
if 'patent-result' in html:
    print("Found patent-result class!")
