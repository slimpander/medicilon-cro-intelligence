import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

# Find ALL rules touching .tab-pane display
print("=== All CSS rules mentioning tab-pane ===")
for i, line in enumerate(lines, 1):
    if 'tab-pane' in line and i < 1200:
        print(f"{i:4d}: {line[:140]}")

print()
# Find the tab click handler - show full content
print("=== Tab click handler ===")
idx = html.find("document.querySelectorAll('.tab-btn').forEach")
ln = html[:idx].count('\n')
for i in range(ln, min(len(lines), ln+25)):
    print(f"{i+1:4d}: {lines[i]}")
