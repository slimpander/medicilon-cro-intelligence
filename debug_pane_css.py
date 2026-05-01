import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

# 1. Show all CSS rules that mention tab-clients or tab-timeline
print("=== CSS rules for tab-clients / tab-timeline ===")
for i, line in enumerate(lines, 1):
    if ('tab-clients' in line or 'tab-timeline' in line) and i < 1100:
        print(f"{i:4d}: {line[:120]}")

print()

# 2. Show the renderClients function call chain
print("=== renderClients call sites ===")
for i, line in enumerate(lines, 1):
    if 'renderClients' in line:
        print(f"{i:4d}: {line[:120]}")

print()
# 3. Show renderTimeline call sites
print("=== renderTimeline call sites ===")
for i, line in enumerate(lines, 1):
    if 'renderTimeline' in line:
        print(f"{i:4d}: {line[:120]}")

print()
# 4. Show tab-clients pane full CSS
print("=== #tab-clients CSS ===")
idx = html.find('#tab-clients')
while idx >= 0:
    ln = html[:idx].count('\n')
    if ln < 1100:  # only CSS section
        print(f"Line {ln+1}: {lines[ln][:120]}")
    idx = html.find('#tab-clients', idx+1)

print()
# 5. Show renderClients function body
def show_fn(fn_name, max_lines=30):
    idx = html.find(f'function {fn_name}(')
    if idx < 0: print(f"NOT FOUND: {fn_name}"); return
    ln = html[:idx].count('\n')
    print(f"=== {fn_name}() at line {ln+1} ===")
    for i in range(ln, min(len(lines), ln+max_lines)):
        print(f"{i+1:4d}: {lines[i]}")

show_fn('renderClients', 15)
show_fn('renderTimeline', 10)
