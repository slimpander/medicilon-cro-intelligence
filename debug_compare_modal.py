import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

def show_fn(fn_name, max_lines=60):
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

# The compare modal HTML
for kw in ['compare-modal-overlay', 'compare-selectors', 'compare-tab-a', 'compare-tab-b',
           'compare-quick-btns', 'vs Charles River']:
    idx = html.find(kw)
    if idx >= 0:
        ln = html[:idx].count('\n')
        print(f"'{kw}' at line {ln+1}:")
        for i in range(max(0,ln-1), min(len(lines), ln+8)):
            print(f"  {i+1:4d}: {lines[i][:140]}")
        print()

# Scoring functions
show_fn('calcOpportunityScore', 40)
show_fn('getMedicilonGaps', 30)
show_fn('getTopOpportunityStates', 20)
show_fn('getServiceWhitespace', 20)
show_fn('getUnderservedStates', 20)
