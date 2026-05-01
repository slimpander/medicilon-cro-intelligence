import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print("=== Tab handler lines 2504-2525 ===")
for i in range(2503, 2525):
    print(f"{i+1:4d}: {lines[i]}", end='')
