import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

def show_around(keyword, context=15):
    idx = html.find(keyword)
    if idx < 0:
        print(f"NOT FOUND: {keyword}")
        return
    lineno = html[:idx].count('\n')
    print(f"\n=== '{keyword}' at line {lineno+1} ===")
    for i in range(max(0,lineno-2), min(len(lines), lineno+context)):
        print(f"{i+1:4d}: {lines[i]}")

# 1. News panel open button handler
show_around("loadNewsData().catch", 10)

# 2. Compare modal
show_around("compare-modal", 8)
show_around("function openCompare", 8)
show_around("compare-btn", 8)

# 3. Export
show_around("function exportReport", 8)
show_around("export-btn", 8)
show_around("html2canvas", 8)
