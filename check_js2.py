import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Get all script blocks
matches = list(re.finditer(r'<script>([\s\S]*?)</script>', html, re.DOTALL))
print(f"Found {len(matches)} inline script blocks")

# Use the largest one (main app JS)
js = max(matches, key=lambda m: len(m.group(1))).group(1)
print(f"Main JS block: {len(js):,} chars")

# Write to file
with open('_app.js', 'w', encoding='utf-8') as f:
    f.write(js)

import subprocess
# Use acorn or just basic node parse
result = subprocess.run(
    ['node', '-e', f'require("fs").readFileSync("_app.js","utf8"); console.log("OK")'],
    capture_output=True, text=True, cwd='.'
)
print("stderr:", result.stderr[:2000] if result.stderr else "(none)")
print("stdout:", result.stdout)
print("returncode:", result.returncode)

import os; os.remove('_app.js')
