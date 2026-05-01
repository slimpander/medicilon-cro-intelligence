import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Show full init function
idx = html.find('function init(){')
print("init() declaration:", repr(html[idx:idx+20]))
print()
# Show where init() is called
import re
for m in re.finditer(r'\binit\s*\(\s*\)', html):
    print(f"init() called at {m.start()}:", html[m.start()-50:m.start()+50])
    print()
