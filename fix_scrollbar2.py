import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

original_len = len(html)

# Replace the global scrollbar rule (line 364-367) — this covers most elements
OLD_GLOBAL = """::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--border-bright); }"""

NEW_GLOBAL = """::-webkit-scrollbar { width: 7px; height: 7px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); border-radius: 4px; }
::-webkit-scrollbar-thumb { background: #3a5570; border-radius: 4px; border: 1px solid rgba(255,255,255,0.05); }
::-webkit-scrollbar-thumb:hover { background: #4d7099; }"""

# Also patch all individual element scrollbars
REPLACEMENTS = [
    # sidebar
    ("#sidebar-inner::-webkit-scrollbar { width: 4px; }",
     "#sidebar-inner::-webkit-scrollbar { width: 7px; }"),
    # detail body
    ("#detail-body::-webkit-scrollbar { width: 4px; }",
     "#detail-body::-webkit-scrollbar { width: 7px; }"),
    # tab pane (horizontal)
    (".tab-pane::-webkit-scrollbar { height: 4px; }",
     ".tab-pane::-webkit-scrollbar { height: 7px; }"),
    # news
    ("#news-body::-webkit-scrollbar { width: 4px; }",
     "#news-body::-webkit-scrollbar { width: 7px; }"),
    # cro modal
    ("#cro-modal-body::-webkit-scrollbar { width: 4px; }",
     "#cro-modal-body::-webkit-scrollbar { width: 7px; }"),
    # compare tab
    ("#compare-tab-body::-webkit-scrollbar { width: 4px; }",
     "#compare-tab-body::-webkit-scrollbar { width: 7px; }"),
    # clients body (horizontal)
    ("#clients-body::-webkit-scrollbar { height: 4px; }",
     "#clients-body::-webkit-scrollbar { height: 7px; }"),
    # thumb colors — replace all var(--border) in scrollbar context
    ("scrollbar-thumb { background: var(--border); border-radius: 2px; }",
     "scrollbar-thumb { background: #3a5570; border-radius: 4px; }"),
]

count = 0
if OLD_GLOBAL in html:
    html = html.replace(OLD_GLOBAL, NEW_GLOBAL, 1)
    count += 1
    print("Replaced global scrollbar rule")

for old, new in REPLACEMENTS:
    n = html.count(old)
    if n:
        html = html.replace(old, new)
        count += n
        print(f"Replaced {n}x: {old[:50]}...")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nDone: {original_len:,} -> {len(html):,} bytes | {count} replacements")
