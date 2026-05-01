import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

def show_fn(fn_name, max_lines=80):
    idx = html.find(f'function {fn_name}')
    if idx < 0:
        print(f"NOT FOUND: function {fn_name}\n"); return
    lineno = html[:idx].count('\n')
    print(f"=== function {fn_name}() at line {lineno+1} ===")
    depth = 0; started = False
    for i in range(lineno, min(len(lines), lineno + max_lines)):
        print(f"{i+1:4d}: {lines[i]}")
        for ch in lines[i]:
            if ch == '{': depth += 1; started = True
            elif ch == '}': depth -= 1
        if started and depth == 0:
            break
    print()

# All bottom panel functions
show_fn('renderOpportunities', 60)
show_fn('renderWhitespace', 40)
show_fn('renderUnderserved', 40)

# Find the strategy/timeline tab JS
for kw in ['Medicilon Strategy', 'renderStrategy', 'renderTimeline', 'tab-strategy', 'opportunityScore', 'oppScore']:
    idx = html.find(kw)
    if idx >= 0:
        lineno = html[:idx].count('\n')
        print(f"'{kw}' at line {lineno+1}:")
        for i in range(max(0,lineno-1), min(len(lines), lineno+5)):
            print(f"  {i+1}: {lines[i][:120]}")
        print()
