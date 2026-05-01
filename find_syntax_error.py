import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Show lines 145-155
print("=== Lines 145-155 ===")
for i, line in enumerate(lines[144:155], start=145):
    print(f"{i:4d}: {line}", end='')
