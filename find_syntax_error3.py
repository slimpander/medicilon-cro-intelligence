import sys, re, subprocess
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Write the entire HTML to a JS file stripping HTML tags
# to get the same line numbers as the browser
with open('_full.js', 'w', encoding='utf-8') as f:
    f.write(html)

# Use node to check syntax - it will report line number in the full file
result = subprocess.run(
    ['node', '--check', '_full.js'],
    capture_output=True, text=True
)
print("stderr:", result.stderr[:3000])
print("returncode:", result.returncode)

import os; os.remove('_full.js')
