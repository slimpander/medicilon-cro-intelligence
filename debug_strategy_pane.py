import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html','r',encoding='utf-8') as f:
    lines = f.readlines()
print("=== Lines 1195-1215 (tab pane HTML) ===")
for i in range(1194, 1215):
    print(f"{i+1:4d}: {lines[i]}", end='')
