import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

def show_around(keyword, before=3, after=15):
    idx = html.find(keyword)
    if idx < 0:
        print(f"NOT FOUND: {keyword}\n")
        return
    lineno = html[:idx].count('\n')
    print(f"=== '{keyword}' at line {lineno+1} ===")
    for i in range(max(0,lineno-before), min(len(lines), lineno+after)):
        print(f"{i+1:4d}: {lines[i]}")
    print()

# 1. News close button
show_around('news-close-btn', after=5)
show_around('news-panel-close', after=5)
show_around('id="news-close"', after=5)

# 2. News panel HTML structure
show_around('id="news-panel"', after=20)

# 3. setupNewsPanel close handler
show_around('news-close', after=10)

# 4. Compare modal - what's the dropdown?
show_around('compare-select', after=10)
show_around('compare-modal-body', after=10)
show_around('<select', after=5)
