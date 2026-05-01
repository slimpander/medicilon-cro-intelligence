import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

# Find layout-related CSS: map-container, bottom-panel, main layout
for kw in ['map-container', 'bottom-panel', '#main', 'flex:1', 'height:', 'min-height', 'max-height']:
    for i, line in enumerate(lines, 1):
        if kw in line and ('height' in line or 'flex' in line or 'map' in line.lower() or 'bottom' in line.lower()):
            print(f"{i:4d}: {line[:120]}")
