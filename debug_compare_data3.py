import sys
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

show_fn('getTopOpportunityStates', 50)
show_fn('buildReasons', 40)
show_fn('getServiceWhitespace', 30)
show_fn('getUnderservedStates', 30)
