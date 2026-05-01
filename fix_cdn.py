import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find and show the current atlas fetch block
idx = html.find("d3.json('data/states")
if idx < 0:
    idx = html.find('states-10m.json')
print("Atlas fetch context:")
print(html[idx-100:idx+300])
print()

# Replace the whole try-catch block with a simple one-liner
# Match anything between 'try{' and the closing of the atlas fetch
pattern = r"try\s*\{\s*usGeo\s*=\s*await[\s\S]{0,500}?states-10m\.json['\"][\s\S]{0,200}?\}"
matches = list(re.finditer(pattern, html))
print(f"Found {len(matches)} pattern matches")
for m in matches:
    print("Match:", repr(m.group()[:100]))

if matches:
    m = matches[0]
    html = html[:m.start()] + "usGeo=await d3.json('data/states-10m.json');" + html[m.end():]
    print("Replaced complex try-catch with simple fetch")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done. File size: {len(html):,}")
