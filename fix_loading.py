"""
fix_loading.py
Two fixes:
1. Cache the US atlas JSON locally so CDN failure doesn't block map load
2. Make loadNewsData() non-blocking (don't await it in init chain)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

original_len = len(html)
changes = []

# ── Fix 1: Make CDN fetch resilient with a timeout ────────────────────────────
OLD_CDN = "usGeo=await d3.json('https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json');"
NEW_CDN = (
    "try{\n"
    "      usGeo=await Promise.race([\n"
    "        d3.json('https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json'),\n"
    "        new Promise((_,rej)=>setTimeout(()=>rej(new Error('CDN timeout')),10000))\n"
    "      ]);\n"
    "    }catch(cdnErr){\n"
    "      console.warn('CDN failed, trying unpkg fallback:', cdnErr.message);\n"
    "      usGeo=await d3.json('https://unpkg.com/us-atlas@3/states-10m.json');\n"
    "    }"
)
if OLD_CDN in html:
    html = html.replace(OLD_CDN, NEW_CDN, 1)
    changes.append("Fix 1: CDN fetch now has 10s timeout + unpkg fallback")
else:
    changes.append("WARNING Fix 1: CDN line not found - skipped")

# ── Fix 2: Make loadNewsData non-blocking in setupNewsPanel ──────────────────
# If loadNewsData() is being awaited somewhere in the init chain, it shouldn't be
# It should fire-and-forget so news loading doesn't block map rendering

# Find any 'await loadNewsData()' and strip the await
if 'await loadNewsData()' in html:
    html = html.replace('await loadNewsData()', 'loadNewsData()')
    changes.append("Fix 2: removed 'await' from loadNewsData() call (now fire-and-forget)")
else:
    changes.append("Fix 2: loadNewsData() already non-blocking (no await found)")

# ── Fix 3: Ensure setupNewsPanel doesn't throw ───────────────────────────────
# Wrap the loadNewsData call inside setupNewsPanel in a try-catch
OLD_SETUP = "if (NEWS_DATA.length === 0) { loadNewsData(); } else { renderNewsList(); }"
NEW_SETUP = (
    "if (NEWS_DATA.length === 0) { "
    "loadNewsData().catch(e=>console.warn('[News] load failed:',e)); "
    "} else { try{renderNewsList();}catch(e){console.warn('[News] render failed:',e);} }"
)
if OLD_SETUP in html:
    html = html.replace(OLD_SETUP, NEW_SETUP, 1)
    changes.append("Fix 3: news open handler wrapped in catch")
else:
    changes.append("Fix 3: news open handler pattern not found - skipped")

# ── Fix 4: Wrap setupNewsPanel call itself in try-catch in init() ─────────────
OLD_SETUP_CALL = "setupModeToggle();setupNewsPanel();"
NEW_SETUP_CALL = "setupModeToggle();try{setupNewsPanel();}catch(e){console.warn('[News] setupNewsPanel failed:',e);}"
if OLD_SETUP_CALL in html:
    html = html.replace(OLD_SETUP_CALL, NEW_SETUP_CALL, 1)
    changes.append("Fix 4: setupNewsPanel() call wrapped in try-catch in init()")
else:
    changes.append("Fix 4: setupNewsPanel call pattern not found - skipped")

# ── Write ─────────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"index.html: {original_len:,} -> {len(html):,} bytes")
for c in changes:
    print(" ", c)
