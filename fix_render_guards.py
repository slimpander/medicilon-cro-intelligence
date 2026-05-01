import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

original_len = len(html)
changes = []

# ── Fix 1: Timeline — remove "render once" guard so it renders properly ───────
OLD_TIMELINE_GUARD = (
    "function renderTimeline() {\n"
    "  const pane = document.getElementById('tab-timeline');\n"
    "  if (!pane || pane.dataset.rendered) return;\n"
    "  pane.dataset.rendered = '1';"
)
NEW_TIMELINE_GUARD = (
    "function renderTimeline() {\n"
    "  const pane = document.getElementById('tab-timeline');\n"
    "  if (!pane || !croData) return;\n"
    "  if (pane.dataset.rendered) return;  // already built\n"
    "  pane.dataset.rendered = '1';"
)
if OLD_TIMELINE_GUARD in html:
    html = html.replace(OLD_TIMELINE_GUARD, NEW_TIMELINE_GUARD, 1)
    changes.append("Timeline guard preserved but added croData check")

# The real timeline fix: don't set rendered=1 at init, only when tab is visible
# Remove from renderBottomPanels, let tab click handle it
OLD_BOTTOM = 'function renderBottomPanels(){renderOpportunities();renderWhitespace();renderUnderserved();initCompareTab();renderClients();renderTimeline();}'
NEW_BOTTOM = 'function renderBottomPanels(){renderOpportunities();renderWhitespace();renderUnderserved();initCompareTab();renderClients();}'
if OLD_BOTTOM in html:
    html = html.replace(OLD_BOTTOM, NEW_BOTTOM, 1)
    changes.append("Removed renderTimeline() from renderBottomPanels (lazy-only now)")

# ── Fix 2: Clients — append toolbar+body directly into pane ──────────────────
# Problem: renderClients() runs at init when pane has display:none
# The JS creates toolbar/body but may not be appending to the right element
# Let's simplify: just do it inline, no lazy guard

OLD_RENDER_CLIENTS_HEADER = (
    "function renderClients() {\n"
    "  const pane = document.getElementById('tab-clients');\n"
    "  if (!pane || !croData) return;\n"
    "\n"
    "  // Build toolbar if not yet present\n"
    "  if (!document.getElementById('clients-toolbar')) {"
)
NEW_RENDER_CLIENTS_HEADER = (
    "function renderClients() {\n"
    "  const pane = document.getElementById('tab-clients');\n"
    "  if (!pane || !croData) return;\n"
    "\n"
    "  // Build toolbar if not yet present\n"
    "  if (!document.getElementById('clients-toolbar')) {\n"
    "    pane.innerHTML = ''; // clear any stale content"
)
if OLD_RENDER_CLIENTS_HEADER in html:
    html = html.replace(OLD_RENDER_CLIENTS_HEADER, NEW_RENDER_CLIENTS_HEADER, 1)
    changes.append("Added pane.innerHTML='' clear before rebuilding clients toolbar")

# ── Fix 3: Tab switch — reset timeline rendered flag so it can re-render ──────
OLD_TAB_LAZY = (
    "    if (tab === 'clients') renderClients();\n"
    "    else if (tab === 'timeline') renderTimeline();"
)
NEW_TAB_LAZY = (
    "    if (tab === 'clients') renderClients();\n"
    "    else if (tab === 'timeline') {\n"
    "      // Reset rendered flag so it builds fresh\n"
    "      const tlPane = document.getElementById('tab-timeline');\n"
    "      if (tlPane) delete tlPane.dataset.rendered;\n"
    "      renderTimeline();\n"
    "    }"
)
if OLD_TAB_LAZY in html:
    html = html.replace(OLD_TAB_LAZY, NEW_TAB_LAZY, 1)
    changes.append("Timeline tab click resets rendered flag before calling renderTimeline()")

# ── Fix 4: Add explicit pane.appendChild calls in renderClients ───────────────
# Make sure toolbar and body are appended to the pane
OLD_APPEND = (
    "    const body = document.createElement('div');\n"
    "    body.id = 'clients-body';\n"
    "    pane.appendChild(body);\n"
    "\n"
    "    toolbar.querySelector('#client-filter-state').addEventListener"
)
NEW_APPEND = (
    "    const body = document.createElement('div');\n"
    "    body.id = 'clients-body';\n"
    "    pane.appendChild(toolbar);\n"
    "    pane.appendChild(body);\n"
    "\n"
    "    toolbar.querySelector('#client-filter-state').addEventListener"
)
# Check if pane.appendChild(toolbar) is missing
if "pane.appendChild(toolbar)" not in html:
    if OLD_APPEND in html:
        html = html.replace(OLD_APPEND, NEW_APPEND, 1)
        changes.append("Fixed: added pane.appendChild(toolbar) before pane.appendChild(body)")
    else:
        # Try to find and fix any version
        idx = html.find("body.id = 'clients-body';")
        if idx >= 0:
            # Find next pane.appendChild
            next_append = html.find('pane.appendChild(body)', idx)
            if next_append >= 0:
                old_chunk = html[idx:next_append + len('pane.appendChild(body);')]
                new_chunk = "body.id = 'clients-body';\n    pane.appendChild(toolbar);\n    pane.appendChild(body);"
                html = html.replace(old_chunk, new_chunk, 1)
                changes.append("Fixed toolbar append (alt method)")
else:
    changes.append("pane.appendChild(toolbar) already present")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"index.html: {original_len:,} -> {len(html):,} bytes\n")
for c in changes:
    print(f"  OK {c}")

# Verify the clients render function looks right now
with open('index.html', 'r', encoding='utf-8') as f:
    html2 = f.read()
lines2 = html2.split('\n')
idx = html2.find('function renderClients()')
ln = html2[:idx].count('\n')
print(f"\nrenderClients() body (lines {ln+1}-{ln+25}):")
for i in range(ln, min(len(lines2), ln+25)):
    print(f"  {i+1}: {lines2[i]}")
