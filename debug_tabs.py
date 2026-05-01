import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

# Find tab buttons and panes
for i, line in enumerate(lines, 1):
    if 'tab-btn' in line or 'tab-pane' in line or 'data-tab' in line or 'bottom-content' in line or 'bottom-tabs' in line:
        print(f"{i:4d}: {line[:140]}")
