import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

for i, line in enumerate(lines, 1):
    if '--bottom-h' in line or '--topbar-h' in line or ':root' in line or '--sidebar' in line:
        print(f"{i:4d}: {line[:120]}")
