import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    all_lines = f.readlines()

print("=== Lines 1062-1120 (full script start + loadNewsData) ===")
for i in range(1061, 1120):
    print(f"{i+1:4d}: {all_lines[i]}", end='')
