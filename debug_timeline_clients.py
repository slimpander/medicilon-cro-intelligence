import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

def show_fn(fn_name, max_lines=60):
    idx = html.find(f'function {fn_name}')
    if idx < 0: print(f"NOT FOUND: function {fn_name}\n"); return
    lineno = html[:idx].count('\n')
    print(f"=== function {fn_name}() at line {lineno+1} ===")
    depth = 0; started = False
    for i in range(lineno, min(len(lines), lineno + max_lines)):
        print(f"{i+1:4d}: {lines[i]}")
        for ch in lines[i]:
            if ch == '{': depth += 1; started = True
            elif ch == '}': depth -= 1
        if started and depth == 0: break
    print()

# 1. renderClients
show_fn('renderClients', 20)

# 2. Timeline tab — any render function?
for kw in ['renderTimeline', 'tab-timeline', 'function.*[Tt]imeline']:
    for m in re.finditer(kw, html):
        ln = html[:m.start()].count('\n')
        print(f"'{kw}' at line {ln+1}: {lines[ln][:120]}")
    print()

# 3. renderBottomPanels
show_fn('renderBottomPanels', 5)

# 4. Tab switching logic — does it call render on tab switch?
idx = html.find('tab-btn')
ln = html[:idx].count('\n')
print(f"Tab switch handler at line {ln+1}:")
for i in range(ln, min(len(lines), ln+20)):
    print(f"  {i+1}: {lines[i][:120]}")
