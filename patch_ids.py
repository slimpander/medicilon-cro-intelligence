import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

fixes = 0

# Fix news panel button IDs to match what setupNewsPanel() expects
replacements = [
    ('id="news-minimize"', 'id="news-minimize-btn"'),
    ('id="news-close"',    'id="news-close-btn"'),
    ('id="news-refresh-btn"', 'id="news-refresh-btn"'),  # this one is fine already
]
for old, new in replacements:
    if old in html and old != new:
        html = html.replace(old, new, 1)
        fixes += 1
        print(f"Fixed: {old} -> {new}")
    elif old in html:
        print(f"OK (unchanged): {old}")
    else:
        print(f"NOT FOUND: {old}")

# Also check if news-open-btn onclick wires correctly
if "id=\"news-open-btn\"" in html:
    print("OK: news-open-btn exists")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done. {fixes} fixes. Size: {len(html)}")
