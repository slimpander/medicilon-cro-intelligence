import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

# Find all scrollbar rules
print("=== All scrollbar CSS ===")
for i, line in enumerate(lines, 1):
    if 'scrollbar' in line.lower() and i < 1200:
        print(f"{i:4d}: {line[:120]}")
