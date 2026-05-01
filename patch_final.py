"""patch_final.py — Clean up and add only what's truly missing."""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

print(f"Starting: {len(html)} bytes")
fixes = 0

# ── 1. Remove our duplicate CSS block (the one with /* ── News Panel ── */ we added)
# The real CSS is already in Claude's version. Our appended CSS may duplicate #news-panel rules.
# Find and remove our injected block (it starts with our specific NEWS_CSS marker)
# Our block started with: "/* ── News Panel ─────────────────────────────────── */"
# and ended with: "#news-open-btn:hover { border-color: var(--accent); color: var(--accent); }"
# Then we added company modal CSS and strategy CSS

# Instead of trying to remove it, let's just check if it's causing visual conflicts
# Our added CSS has: #news-panel.visible { display: flex; }
# The real CSS has: #news-panel.hidden { display: none; }
# These are compatible (different selectors), shouldn't conflict

# ── 2. Add modal overlay HTML if missing ─────────────────────────────────────
if 'id="cro-modal-overlay"' not in html:
    MODAL_HTML = '''
<!-- CRO Company Profile Modal -->
<div id="cro-modal-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,0.65);z-index:300;display:none;align-items:center;justify-content:center;backdrop-filter:blur(2px)">
  <div id="cro-modal" style="background:var(--surface);border:1px solid var(--border);border-radius:12px;width:540px;max-width:92vw;max-height:82vh;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(0,0,0,0.6);overflow:hidden">
    <div id="cro-modal-header" style="padding:18px 20px 14px;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;gap:12px">
      <div id="cro-modal-dot" style="width:14px;height:14px;border-radius:50%;flex-shrink:0;margin-top:3px"></div>
      <div style="flex:1">
        <div id="cro-modal-title" style="font-size:17px;font-weight:700"></div>
        <div id="cro-modal-sub" style="font-size:11px;color:var(--text-muted);margin-top:3px"></div>
      </div>
      <button id="cro-modal-close" style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:18px;padding:2px 6px;border-radius:4px;font-family:inherit">&#x2715;</button>
    </div>
    <div id="cro-modal-body" style="flex:1;overflow-y:auto;padding:18px 20px"></div>
  </div>
</div>
'''
    # Insert before </body>
    html = html.replace('</body>', MODAL_HTML + '</body>', 1)
    fixes += 1
    print("OK: Modal overlay HTML added")
else:
    print("OK: Modal overlay already present")

# ── 3. Add strategy tab pane if not present ──────────────────────────────────
if 'id="tab-strategy"' not in html:
    # Find the underserved pane and add after it
    # Look for the closing div of the bottom-content area
    old_bottom = 'id="tab-underserved"'
    idx = html.find(old_bottom)
    if idx != -1:
        # Find the end of that element
        end = html.find('>', idx) + 1
        html = html[:end] + '\n        <div class="tab-pane" id="tab-strategy" style="overflow-y:auto;padding:0"></div>' + html[end:]
        fixes += 1
        print("OK: Strategy tab pane added")
    else:
        print("WARNING: tab-underserved not found")
else:
    print("OK: Strategy pane already present")

# ── 4. Add strategy tab button if not present ────────────────────────────────
if 'data-tab="strategy"' not in html:
    old_tab = 'data-tab="underserved"'
    idx = html.find(old_tab)
    if idx != -1:
        end = html.find('</button>', idx) + 9
        html = html[:end] + '\n        <button class="tab-btn" data-tab="strategy">&#128202; Medicilon Strategy</button>' + html[end:]
        fixes += 1
        print("OK: Strategy tab button added")
    else:
        print("WARNING: underserved tab button not found")
else:
    print("OK: Strategy tab button already present")

# ── 5. Wire strategy tab render in tab click handler ─────────────────────────
if 'renderStrategyPanel' not in html:
    print("WARNING: renderStrategyPanel not in file - add JS first")
else:
    # Check if wired to tab click
    tab_click_area = html[html.find("querySelectorAll('.tab-btn')"):html.find("querySelectorAll('.tab-btn')")+300]
    if 'renderStrategyPanel' not in tab_click_area:
        # Wire it up
        old_wire = "if(btn.dataset.tab==='strategy')renderStrategyPanel();"
        if old_wire not in html:
            # Find the tab click and add it
            old_tab_end = "if(pane)pane.classList.add('active');"
            new_tab_end = "if(pane)pane.classList.add('active');if(btn.dataset.tab==='strategy')renderStrategyPanel();"
            if old_tab_end in html:
                html = html.replace(old_tab_end, new_tab_end, 1)
                fixes += 1
                print("OK: Strategy render wired to tab click")
    else:
        print("OK: Strategy render already wired")

# ── 6. Wire openCroModal to company legend clicks ────────────────────────────
# Check current state of legend
if "openCroModal(cro.id)" in html:
    print("OK: openCroModal already wired in legend")
else:
    print("WARNING: openCroModal not found in legend - may need manual check")

# ── 7. Write ──────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"\nDone. {fixes} fixes applied. Final size: {len(html)}")

# Final verification
checks = {
    'cro-modal-overlay': 'id="cro-modal-overlay"',
    'tab-strategy pane': 'id="tab-strategy"',
    'strategy tab btn': 'data-tab="strategy"',
    'renderStrategyPanel JS': 'function renderStrategyPanel',
    'openCroModal JS': 'function openCroModal',
    'estimateClients JS': 'function estimateClients',
    'news.google.com': 'news.google.com',
    'openCroModal legend': 'openCroModal(cro.id)',
}
print("\nFinal checks:")
for label, needle in checks.items():
    print(f"  {'OK' if needle in html else 'MISSING'}  {label}")
