import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = html.split('\n')

original_len = len(html)
changes = []

# ── 1. Add renderTimeline() to renderBottomPanels() ──────────────────────────
OLD_BOTTOM = 'function renderBottomPanels(){renderOpportunities();renderWhitespace();renderUnderserved();initCompareTab();renderClients();}'
NEW_BOTTOM = 'function renderBottomPanels(){renderOpportunities();renderWhitespace();renderUnderserved();initCompareTab();renderClients();renderTimeline();}'
if OLD_BOTTOM in html:
    html = html.replace(OLD_BOTTOM, NEW_BOTTOM, 1)
    changes.append("Added renderTimeline() to renderBottomPanels()")

# ── 2. Fix tab switching to call render functions on demand ───────────────────
# Find the tab-btn click handler
tab_handler_idx = html.find("document.querySelectorAll('.tab-btn').forEach(btn=>{")
if tab_handler_idx < 0:
    tab_handler_idx = html.find("querySelectorAll('.tab-btn')")

ln = html[:tab_handler_idx].count('\n')
print(f"Tab handler at HTML line {ln+1}")

# Show it
for i in range(ln, min(len(lines), ln+15)):
    print(f"  {i+1}: {lines[i][:140]}")
print()

# Find the exact tab click handler and add lazy render calls
OLD_TAB_HANDLER = "document.querySelectorAll('.tab-btn').forEach(btn=>{\n  btn.addEventListener('click',()=>{"
if OLD_TAB_HANDLER not in html:
    # Try alternate whitespace
    OLD_TAB_HANDLER = "document.querySelectorAll('.tab-btn').forEach(btn=>{"

idx = html.find(OLD_TAB_HANDLER)
if idx >= 0:
    # Find the body of the click handler - look for pane.classList.add
    add_after = html.find("if(pane)pane.classList.add('active');", idx)
    if add_after >= 0:
        line_end = html.find('\n', add_after)
        old_line = html[add_after:line_end]
        new_line = old_line + (
            "\n    // Lazy render on tab switch\n"
            "    const tab = btn.dataset.tab;\n"
            "    if (tab === 'clients') renderClients();\n"
            "    else if (tab === 'timeline') renderTimeline();\n"
            "    else if (tab === 'opportunities') renderOpportunities();\n"
            "    else if (tab === 'whitespace') renderWhitespace();\n"
            "    else if (tab === 'underserved') renderUnderserved();"
        )
        html = html.replace(old_line, new_line, 1)
        changes.append("Added lazy render calls in tab switch handler")

# ── 3. Fix renderClients to always rebuild cards ──────────────────────────────
# The issue: renderClients() only builds toolbar once, but _renderClientCards
# may fail if croData isn't ready. Make it more robust.
OLD_RENDER_CLIENTS = "function renderClients() {\n  const pane = document.getElementById('tab-clients');\n  if (!pane) return;"
NEW_RENDER_CLIENTS = "function renderClients() {\n  const pane = document.getElementById('tab-clients');\n  if (!pane || !croData) return;"
if OLD_RENDER_CLIENTS in html:
    html = html.replace(OLD_RENDER_CLIENTS, NEW_RENDER_CLIENTS, 1)
    changes.append("Added croData guard to renderClients()")

# ── 4. Fix _renderClientCards croData guard ───────────────────────────────────
OLD_CARDS = "function _renderClientCards() {\n  const body = document.getElementById('clients-body');\n  const countEl = document.getElementById('clients-count');\n  if (!body) return;"
NEW_CARDS = "function _renderClientCards() {\n  const body = document.getElementById('clients-body');\n  const countEl = document.getElementById('clients-count');\n  if (!body || !croData) return;"
if OLD_CARDS in html:
    html = html.replace(OLD_CARDS, NEW_CARDS, 1)
    changes.append("Added croData guard to _renderClientCards()")

# ── 5. Check what renderTimeline() looks like ─────────────────────────────────
fn_idx = html.find('function renderTimeline()')
fn_ln = html[:fn_idx].count('\n')
print(f"renderTimeline() at line {fn_ln+1}:")
for i in range(fn_ln, min(len(lines), fn_ln+30)):
    print(f"  {i+1}: {lines[i][:120]}")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nindex.html: {original_len:,} -> {len(html):,} bytes")
for c in changes:
    print(f"  OK {c}")
