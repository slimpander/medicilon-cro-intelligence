import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Show context around both init declarations
idx1 = html.find('function init(){')
idx2 = html.find('async function init(){')
print(f"=== idx1={idx1} ===")
print(html[idx1-20:idx1+60])
print()
print(f"=== idx2={idx2} ===")
print(html[idx2-20:idx2+60])
print()
print("Distance:", idx2 - idx1)
