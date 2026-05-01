"""
patch_news_live.py
Patches index.html so the News panel loads from data/news_data.json
(fetched by fetch_news.py) instead of the hardcoded NEWS_DATA array.

Run AFTER fetch_news.py has generated data/news_data.json:
    python fetch_news.py
    python patch_news_live.py
"""

import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# ── Replace static NEWS_DATA array with a dynamic fetch ──────────────────────
OLD_NEWS_DATA_PATTERN = r'// ─── News Data ─+\s*const NEWS_DATA = \[[\s\S]*?\];'

NEW_NEWS_FETCH = """\
// ─── News Data (loaded from data/news_data.json) ─────────────────────────────
let NEWS_DATA = [];
let NEWS_META = {};

async function loadNewsData() {
  try {
    const resp = await fetch('data/news_data.json?t=' + Date.now());
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const json = await resp.json();
    NEWS_DATA = json.articles || [];
    NEWS_META = json.metadata || {};
    console.log('[News] Loaded ' + NEWS_DATA.length + ' articles, cutoff: ' + (NEWS_META.cutoff_date || 'unknown'));
    renderNewsList();
    // Update footer with metadata
    const countEl = document.getElementById('news-count-label');
    if (countEl && NEWS_META.generated) {
      const d = new Date(NEWS_META.generated);
      const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      countEl.title = 'Data fetched: ' + label + ' | Lookback: ' + (NEWS_META.lookback_years || 3) + ' years';
    }
  } catch (e) {
    console.warn('[News] Could not load news_data.json, falling back to empty list:', e.message);
    NEWS_DATA = [];
    renderNewsList();
  }
}
"""

if re.search(OLD_NEWS_DATA_PATTERN, html):
    html = re.sub(OLD_NEWS_DATA_PATTERN, NEW_NEWS_FETCH, html)
    print("✓ Replaced static NEWS_DATA with dynamic fetch")
else:
    # Fallback: insert before the initNewsPanel function
    INSERT_BEFORE = 'let newsFilter = {'
    if INSERT_BEFORE in html:
        html = html.replace(INSERT_BEFORE, NEW_NEWS_FETCH + '\n' + INSERT_BEFORE, 1)
        print("✓ Inserted dynamic news loader before newsFilter")
    else:
        print("WARNING: Could not find NEWS_DATA insertion point — check index.html manually")

# ── Patch initNewsPanel to call loadNewsData() on open ───────────────────────
OLD_OPEN_HANDLER = """\
  openBtn.addEventListener('click', () => {
    panel.classList.toggle('visible');
    if (panel.classList.contains('visible')) { panel.classList.remove('minimized'); renderNewsList(); }
  });"""

NEW_OPEN_HANDLER = """\
  openBtn.addEventListener('click', () => {
    panel.classList.toggle('visible');
    if (panel.classList.contains('visible')) {
      panel.classList.remove('minimized');
      if (NEWS_DATA.length === 0) {
        loadNewsData();
      } else {
        renderNewsList();
      }
    }
  });"""

if OLD_OPEN_HANDLER in html:
    html = html.replace(OLD_OPEN_HANDLER, NEW_OPEN_HANDLER, 1)
    print("✓ Patched open button to call loadNewsData() on first open")
else:
    print("WARNING: Could not find open button handler — news may not auto-load")

# ── Patch refresh button to reload from server ────────────────────────────────
OLD_REFRESH = "if (refreshBtn) refreshBtn.addEventListener('click', renderNewsList);"
NEW_REFRESH = "if (refreshBtn) refreshBtn.addEventListener('click', () => { NEWS_DATA = []; loadNewsData(); });"

if OLD_REFRESH in html:
    html = html.replace(OLD_REFRESH, NEW_REFRESH, 1)
    print("✓ Patched refresh button to re-fetch from server")
else:
    print("WARNING: Could not find refresh button handler")

# ── Add data freshness indicator to news footer ───────────────────────────────
OLD_FOOTER = '<span class="news-count" id="news-count-label">— items</span>'
NEW_FOOTER = '<span class="news-count" id="news-count-label" title="Hover for fetch date">— items</span>'

if OLD_FOOTER in html:
    html = html.replace(OLD_FOOTER, NEW_FOOTER, 1)
    print("✓ Added freshness tooltip to news count label")

# ── Write output ──────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nDone. index.html updated ({len(html):,} bytes)")
print("\nWorkflow:")
print("  1. python fetch_news.py          # fetch real news (3yr window)")
print("  2. python patch_news_live.py     # (only needed once, already run)")
print("  3. python -m http.server 8000    # serve locally")
print("  4. open http://localhost:8000    # view in browser")
print("\nTo refresh news data later, just re-run: python fetch_news.py")
