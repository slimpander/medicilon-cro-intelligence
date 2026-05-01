import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re

# 1. Find loading hide
patterns = [
    "loading').style.display",
    "getElementById('loading')",
    "loading.style",
    "style.display = 'none'",
]
for p in patterns:
    idx = html.find(p)
    if idx >= 0:
        print(f"Found '{p}' at {idx}:")
        print(html[idx-100:idx+150])
        print()

# 2. Find all fetch() calls
print("=== fetch() calls ===")
for m in re.finditer(r"fetch\s*\(", html):
    print(m.start(), html[m.start():m.start()+100])
print()

# 3. Find Promise.all
print("=== Promise.all ===")
for m in re.finditer(r"Promise\.all", html):
    print(m.start(), html[m.start():m.start()+200])
print()

# 4. Find init function
print("=== init/window.onload ===")
for m in re.finditer(r"(function init\b|window\.onload|window\.addEventListener\('load')", html):
    print(m.start(), html[m.start():m.start()+300])
    print()
