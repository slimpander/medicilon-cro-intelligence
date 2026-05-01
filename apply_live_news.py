"""
apply_live_news.py
Directly patches index.html to replace hardcoded NEWS_DATA with
a dynamic fetch from data/news_data.json (3-year filtered data).
"""

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

original_len = len(html)

# ── 1. Replace static NEWS_DATA array with dynamic loader ────────────────────
start = html.find('const NEWS_DATA = [')
if start < 0:
    print("ERROR: Could not find 'const NEWS_DATA = [' in index.html")
    exit(1)

# Walk forward to find the matching closing bracket
depth = 0
i = start + len('const NEWS_DATA = [')
while i < len(html):
    if html[i] == '[':
        depth += 1
    elif html[i] == ']':
        if depth == 0:
            break
        depth -= 1
    i += 1
array_end = i + 1  # include the ']' itself

NEW_LOADER = (
    "let NEWS_DATA = [];\n"
    "let NEWS_META = {};\n"
    "\n"
    "async function loadNewsData() {\n"
    "  try {\n"
    "    const resp = await fetch('data/news_data.json?t=' + Date.now());\n"
    "    if (!resp.ok) throw new Error('HTTP ' + resp.status);\n"
    "    const json = await resp.json();\n"
    "    NEWS_DATA = json.articles || [];\n"
    "    NEWS_META = json.metadata || {};\n"
    "    console.log('[News] Loaded ' + NEWS_DATA.length + ' articles, cutoff: ' + (NEWS_META.cutoff_date || 'unknown'));\n"
    "    renderNewsList();\n"
    "    const countEl = document.getElementById('news-count-label');\n"
    "    if (countEl && NEWS_META.generated) {\n"
    "      const d = new Date(NEWS_META.generated);\n"
    "      const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });\n"
    "      countEl.title = 'Fetched: ' + label + ' | Lookback: ' + (NEWS_META.lookback_years || 3) + ' years';\n"
    "    }\n"
    "  } catch (e) {\n"
    "    console.warn('[News] Could not load news_data.json:', e.message);\n"
    "    NEWS_DATA = [];\n"
    "    renderNewsList();\n"
    "  }\n"
    "}"
)

html = html[:start] + NEW_LOADER + html[array_end:]
print(f"Step 1 done: replaced static NEWS_DATA ({array_end - start} chars) with dynamic loader")

# ── 2. Patch news button to load data on first open ──────────────────────────
# Find the news-open-btn click handler — look for the getElementById call
btn_marker = "getElementById('news-open-btn')"
btn_idx = html.find(btn_marker)
if btn_idx >= 0:
    # Find the start of the addEventListener call on this element
    # Pattern: document.getElementById('news-open-btn').addEventListener('click', () => { ... });
    # OR: document.getElementById('news-open-btn').onclick = ...
    # Find the .addEventListener or .onclick after the marker
    handler_start = btn_idx + len(btn_marker)
    # Look ahead for the opening brace of the handler body
    brace_idx = html.find('{', handler_start)
    paren_close = html.find(');', brace_idx)
    if brace_idx > 0 and paren_close > brace_idx:
        old_handler_body = html[brace_idx:paren_close + 2]
        new_handler_body = (
            "{\n"
            "    const panel = document.getElementById('news-panel');\n"
            "    panel.classList.toggle('visible');\n"
            "    if (panel.classList.contains('visible')) {\n"
            "      panel.classList.remove('minimized');\n"
            "      if (NEWS_DATA.length === 0) { loadNewsData(); } else { renderNewsList(); }\n"
            "    }\n"
            "  });"
        )
        html = html[:brace_idx] + new_handler_body + html[paren_close + 2:]
        print("Step 2 done: patched open button to call loadNewsData() on first open")
    else:
        print("WARNING: Could not find handler body for news-open-btn")
else:
    print("WARNING: Could not find news-open-btn in HTML — skipping step 2")

# ── 3. Patch refresh button to re-fetch ──────────────────────────────────────
old_refresh_a = "addEventListener('click', renderNewsList)"
old_refresh_b = "addEventListener('click', () => { NEWS_DATA = []; loadNewsData(); })"
if old_refresh_a in html:
    html = html.replace(old_refresh_a, "addEventListener('click', () => { NEWS_DATA = []; loadNewsData(); })", 1)
    print("Step 3 done: patched refresh button")
elif old_refresh_b in html:
    print("Step 3: refresh button already patched")
else:
    # Try to find the refresh btn assignment
    ref_idx = html.find("news-refresh-btn")
    if ref_idx >= 0:
        # Look for its click handler
        ref_click = html.find("renderNewsList", ref_idx)
        if ref_click > 0 and ref_click - ref_idx < 500:
            html = html[:ref_click] + "() => { NEWS_DATA = []; loadNewsData(); }" + html[ref_click + len("renderNewsList"):]
            print("Step 3 done: patched refresh button (alt method)")
        else:
            print("WARNING: Could not find refresh button click handler")
    else:
        print("WARNING: Could not find news-refresh-btn")

# ── 4. Add loadNewsData() call on panel open in the initNewsPanel function ───
# If initNewsPanel initializes things on load, we should call loadNewsData() there too
init_marker = "function initNewsPanel()"
init_idx = html.find(init_marker)
if init_idx >= 0:
    # Find the closing brace of initNewsPanel
    # Insert loadNewsData() call near the end of the function
    # Simple approach: find 'renderNewsList();' calls inside initNewsPanel and replace first
    render_inside = html.find("renderNewsList();", init_idx)
    if render_inside > 0 and render_inside - init_idx < 3000:
        html = html[:render_inside] + "loadNewsData();" + html[render_inside + len("renderNewsList();"):]
        print("Step 4 done: replaced initial renderNewsList() with loadNewsData() in initNewsPanel")
    else:
        print("Step 4: no renderNewsList() found in initNewsPanel (ok — lazy load on open)")
else:
    print("WARNING: initNewsPanel not found")

# ── Write output ──────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nDone. index.html: {original_len:,} -> {len(html):,} bytes")
print("\nWorkflow going forward:")
print("  python fetch_news.py          # refresh news (3-year window)")
print("  python -m http.server 8000    # serve locally")
print("  http://localhost:8000         # view in browser")
