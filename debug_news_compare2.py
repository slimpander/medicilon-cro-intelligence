import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

def show_around(keyword, before=2, after=30):
    idx = html.find(keyword)
    if idx < 0:
        print(f"NOT FOUND: {keyword}\n"); return
    lineno = html[:idx].count('\n')
    print(f"=== '{keyword}' at line {lineno+1} ===")
    for i in range(max(0,lineno-before), min(len(lines), lineno+after)):
        print(f"{i+1:4d}: {lines[i]}")
    print()

# Full compare modal HTML
show_around('compare-modal-overlay', after=40)

# setupNewsPanel function
show_around('function setupNewsPanel', after=40)
