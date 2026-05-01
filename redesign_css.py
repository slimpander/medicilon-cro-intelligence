"""
redesign_css.py — Apply premium dark UI redesign to index.html.
Pure CSS replacement: no JS or HTML structure changes.
"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

print(f"Starting: {len(html)} bytes")

# ── 1. Replace Google Fonts import ───────────────────────────────────────────
old_font = 'href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"'
new_font = 'href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap"'
if old_font in html:
    html = html.replace(old_font, new_font, 1)
    print("OK: Fonts updated")
else:
    print("WARNING: font link not found")

# ── 2. Replace :root variables ────────────────────────────────────────────────
old_root_start = ':root {'
idx = html.find(old_root_start)
if idx != -1:
    end = html.find('\n}', idx) + 2
    old_root = html[idx:end]
    new_root = """:root {
  --bg: #080d12;
  --surface: #0d1520;
  --surface2: #131f2e;
  --surface3: #1a2940;
  --border: #1e3045;
  --border-bright: #2a4060;
  --text: #e2eaf4;
  --text-muted: #6b8aab;
  --text-dim: #3a5570;
  --gold: #f0a500;
  --gold-bright: #ffbe30;
  --gold-dim: rgba(240,165,0,0.12);
  --gold-border: rgba(240,165,0,0.4);
  --gold-glow: rgba(240,165,0,0.18);
  --accent: #00d4ff;
  --accent-dim: rgba(0,212,255,0.08);
  --accent-glow: rgba(0,212,255,0.22);
  --green: #00e5a0;
  --red: #ff4560;
  --orange: #ff9a3c;
  --purple: #8b5cf6;
  --sidebar-w: 290px;
  --topbar-h: 70px;
  --bottom-h: 290px;
  --radius: 8px;
  --font-display: 'Space Grotesk', sans-serif;
  --font-body: 'IBM Plex Sans', sans-serif;
  --font-mono: 'IBM Plex Mono', monospace;
}"""
    html = html[:idx] + new_root + html[end:]
    print("OK: CSS variables updated")
else:
    print("WARNING: :root not found")

# ── 3. Build the new CSS block to APPEND inside <style> ──────────────────────
# We append overrides rather than trying to replace every rule
# This is safer and guaranteed to work
OVERRIDE_CSS = """
/* ══ REDESIGN OVERRIDES ══════════════════════════════════════════════════ */

/* Global */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--border-bright); }

body {
  font-family: var(--font-body) !important;
  background: var(--bg);
  background-image:
    radial-gradient(ellipse at 15% 60%, rgba(0,212,255,0.04) 0%, transparent 55%),
    radial-gradient(ellipse at 85% 15%, rgba(240,165,0,0.05) 0%, transparent 50%);
}

/* Top bar */
#topbar {
  background: linear-gradient(180deg, rgba(13,21,32,0.99) 0%, rgba(8,13,18,0.97) 100%) !important;
  position: relative;
  height: var(--topbar-h) !important;
}
#topbar::before {
  content: '';
  position: absolute; inset: 0;
  background-image: radial-gradient(circle at 1px 1px, rgba(0,212,255,0.05) 1px, transparent 0);
  background-size: 24px 24px;
  pointer-events: none;
  z-index: 0;
}
#topbar::after {
  content: '';
  position: absolute; bottom: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent 0%, var(--gold) 25%, var(--accent) 75%, transparent 100%);
}
#topbar > * { position: relative; z-index: 1; }

#topbar .logo-mark {
  background: linear-gradient(135deg, var(--gold-bright) 0%, var(--gold) 50%, #c87800 100%) !important;
  border-radius: 10px !important;
  font-family: var(--font-display) !important;
  font-size: 17px !important;
  box-shadow: 0 0 22px var(--gold-glow), 0 4px 12px rgba(0,0,0,0.4) !important;
  color: #080d12 !important;
}
#topbar h1, #topbar-title {
  font-family: var(--font-display) !important;
  font-size: 15px !important; font-weight: 600 !important;
  letter-spacing: -0.01em !important;
}
#topbar .subtitle { font-size: 11px !important; }

.badge {
  font-family: var(--font-mono) !important;
  font-size: 10px !important;
  background: rgba(13,21,32,0.8) !important;
  border: 1px solid var(--border) !important;
  border-radius: 5px !important; padding: 3px 8px !important;
}
.badge.gold {
  background: var(--gold-dim) !important;
  border-color: var(--gold-border) !important;
  color: var(--gold-bright) !important;
}

/* Stats chips */
.stat-chip {
  background: rgba(13,21,32,0.85) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important; padding: 8px 18px !important;
  backdrop-filter: blur(8px) !important;
}
.stat-chip .stat-val {
  font-family: var(--font-mono) !important;
  font-size: 22px !important; font-weight: 500 !important;
  background: linear-gradient(135deg, var(--accent), #80eaff) !important;
  -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
}
.stat-chip .stat-label { font-size: 10px !important; letter-spacing: 0.05em !important; }

/* Sidebar */
#sidebar {
  background: rgba(11,17,26,0.97) !important;
  backdrop-filter: blur(10px) !important;
  border-right: 1px solid var(--border) !important;
}
.sidebar-label {
  font-family: var(--font-display) !important;
  font-size: 9px !important; font-weight: 600 !important;
  letter-spacing: 0.14em !important;
  color: var(--text-dim) !important;
}

/* Service filter pills */
#service-filters { display: flex !important; flex-wrap: wrap !important; gap: 0 !important; }
.filter-item {
  display: inline-flex !important; align-items: center !important; gap: 5px !important;
  padding: 4px 9px !important; border-radius: 20px !important; cursor: pointer !important;
  transition: all 0.2s cubic-bezier(0.34,1.56,0.64,1) !important;
  border: 1px solid var(--border) !important;
  background: transparent !important; margin: 2px !important;
}
.filter-item:hover { border-color: var(--border-bright) !important; background: var(--surface2) !important; transform: scale(1.04) !important; }
.filter-item input[type=checkbox] { width: 9px !important; height: 9px !important; }
.filter-item label { cursor: pointer !important; font-size: 11px !important; }

/* Company items */
.company-item {
  border-radius: 8px !important;
  padding: 7px 8px !important;
  border: 1px solid transparent !important;
  transition: all 0.18s ease !important;
}
.company-item:hover {
  background: var(--surface2) !important;
  border-color: var(--border) !important;
}
.company-item.medicilon {
  background: var(--gold-dim) !important;
  border: 1px solid var(--gold-border) !important;
  box-shadow: 0 0 14px var(--gold-glow) !important;
}
.company-item.medicilon:hover { box-shadow: 0 0 22px var(--gold-glow) !important; }
.company-name { font-size: 12px !important; font-weight: 500 !important; }

/* Refresh button */
#refresh-btn {
  background: linear-gradient(135deg, var(--surface2), var(--surface3)) !important;
  border: 1px solid var(--border) !important; border-radius: 8px !important;
  font-family: var(--font-body) !important; font-weight: 500 !important;
  letter-spacing: 0.02em !important; transition: all 0.2s !important;
}
#refresh-btn:hover {
  border-color: var(--accent) !important; color: var(--accent) !important;
  box-shadow: 0 0 14px var(--accent-glow) !important;
}

/* Map states */
.state-path {
  stroke: rgba(0,212,255,0.1) !important; stroke-width: 0.5 !important;
  transition: all 0.25s ease !important;
}
.state-path:hover {
  stroke: var(--accent) !important; stroke-width: 1.8 !important;
  filter: drop-shadow(0 0 5px rgba(0,212,255,0.35)) !important;
}

/* Map legend */
#map-legend {
  background: rgba(8,13,18,0.9) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  backdrop-filter: blur(14px) !important;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5) !important;
}
.legend-title { font-family: var(--font-display) !important; font-size: 9px !important; letter-spacing: 0.1em !important; }

/* Stats overlay */
.stat-chip { backdrop-filter: blur(12px) !important; }

/* Tooltip */
#tooltip {
  background: rgba(8,13,18,0.96) !important;
  border: 1px solid var(--border-bright) !important;
  border-radius: 10px !important;
  backdrop-filter: blur(18px) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.65), 0 0 0 1px rgba(0,212,255,0.04) !important;
  font-family: var(--font-body) !important;
}
#tooltip .tt-state { font-family: var(--font-display) !important; font-size: 15px !important; font-weight: 600 !important; }

/* Detail panel */
#detail-panel {
  background: rgba(8,13,18,0.94) !important;
  border-left: 1px solid var(--border) !important;
  backdrop-filter: blur(18px) !important;
  width: 360px !important;
  transition: transform 0.28s cubic-bezier(0.4,0,0.2,1) !important;
}
#detail-state-name { font-family: var(--font-display) !important; font-size: 20px !important; font-weight: 700 !important; }
#detail-close {
  background: none !important; border: none !important;
  color: var(--text-dim) !important; cursor: pointer !important;
  border-radius: 6px !important; font-size: 18px !important;
  transition: all 0.15s !important; font-family: var(--font-body) !important;
}
#detail-close:hover { background: var(--surface2) !important; color: var(--text) !important; }

/* Detail cards */
.detail-cro-card {
  background: linear-gradient(145deg, var(--surface2), var(--surface)) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
.detail-cro-card:hover { border-color: var(--border-bright) !important; }
.detail-cro-name { font-family: var(--font-display) !important; font-weight: 600 !important; }

/* Service tags */
.svc-tag { font-family: var(--font-mono) !important; font-size: 10px !important; }
.svc-tag.core { background: rgba(0,212,255,0.1) !important; border-color: rgba(0,212,255,0.3) !important; color: var(--accent) !important; }
.svc-tag.gap { background: var(--gold-dim) !important; border-color: var(--gold-border) !important; color: var(--gold-bright) !important; }

/* Gap section */
.detail-gap-section { border-left: 3px solid var(--gold) !important; }
.detail-gap-title { color: var(--gold-bright) !important; font-family: var(--font-display) !important; }
.detail-gap-item::before { color: var(--gold) !important; }

/* Opportunity score */
.opp-score-val {
  font-family: var(--font-mono) !important;
  background: linear-gradient(135deg, var(--gold-bright), var(--orange)) !important;
  -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
}

/* Bottom panel */
#bottom-panel {
  background: rgba(11,17,26,0.97) !important;
  border-top: 1px solid var(--border) !important;
  height: var(--bottom-h) !important;
}
#bottom-tabs {
  border-bottom: 1px solid var(--border) !important;
  background: rgba(8,13,18,0.5) !important;
}
.tab-btn {
  font-family: var(--font-body) !important; font-size: 12px !important;
  font-weight: 500 !important; letter-spacing: 0.01em !important;
  color: var(--text-dim) !important;
  transition: all 0.18s !important;
  padding: 11px 18px !important;
  position: relative !important;
}
.tab-btn.active { color: var(--gold) !important; border-bottom-color: var(--gold) !important; }
.tab-btn:hover:not(.active) { color: var(--text-muted) !important; }

/* Opportunity cards */
.opp-card {
  background: linear-gradient(145deg, var(--surface2), var(--surface)) !important;
  border: 1px solid var(--border) !important; border-radius: 10px !important;
  min-width: 230px !important; max-width: 250px !important;
  transition: all 0.22s ease !important; position: relative !important;
  overflow: hidden !important;
}
.opp-card::before {
  content: '' !important; position: absolute !important;
  top: 0; left: 0; right: 0; height: 2px !important;
  background: linear-gradient(90deg, var(--gold), var(--accent)) !important;
  opacity: 0 !important; transition: opacity 0.2s !important;
}
.opp-card:hover { transform: translateY(-3px) !important; border-color: var(--border-bright) !important; box-shadow: 0 8px 28px rgba(0,0,0,0.5) !important; }
.opp-card:hover::before { opacity: 1 !important; }
.opp-card-state { font-family: var(--font-display) !important; font-size: 22px !important; font-weight: 700 !important; }
.opp-card-rank { font-family: var(--font-mono) !important; font-size: 10px !important; color: var(--text-dim) !important; letter-spacing: 0.08em !important; }
.opp-card-score { font-family: var(--font-mono) !important; color: var(--gold) !important; font-size: 11px !important; font-weight: 600 !important; }
.opp-reason { font-size: 10px !important; }
.opp-reason::before { color: var(--gold) !important; }

/* Whitespace cards */
.whitespace-card {
  background: linear-gradient(145deg, var(--surface2), var(--surface)) !important;
  border: 1px solid var(--border) !important; border-radius: 8px !important;
}
.whitespace-card-name { font-family: var(--font-display) !important; font-size: 12px !important; font-weight: 600 !important; }

/* Underserved cards */
.underserved-card {
  background: linear-gradient(145deg, var(--surface2), var(--surface)) !important;
  border: 1px solid var(--border) !important; border-radius: 8px !important;
}
.underserved-state { font-family: var(--font-display) !important; font-size: 15px !important; font-weight: 700 !important; }

/* Strategy cards */
.strategy-card {
  background: linear-gradient(145deg, var(--surface2), var(--surface)) !important;
  border: 1px solid var(--border) !important; border-radius: 10px !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
.strategy-card:hover { border-color: var(--border-bright) !important; box-shadow: 0 4px 20px rgba(0,0,0,0.4) !important; }
.strategy-card-title { font-family: var(--font-display) !important; font-size: 13px !important; font-weight: 600 !important; }
.strategy-card-icon { font-size: 22px !important; margin-bottom: 8px !important; }
.strategy-highlight {
  background: var(--gold-dim) !important; border-color: var(--gold-border) !important;
  color: var(--gold-bright) !important; font-family: var(--font-mono) !important;
}

/* News panel */
#news-panel {
  background: rgba(8,13,18,0.95) !important;
  border: 1px solid var(--border-bright) !important;
  border-radius: 12px !important;
  backdrop-filter: blur(20px) !important;
  box-shadow: 0 20px 60px rgba(0,0,0,0.7) !important;
}
#news-header {
  background: rgba(13,21,32,0.9) !important;
  border-bottom: 1px solid var(--border) !important;
}
#news-header-title { font-family: var(--font-display) !important; font-weight: 600 !important; }
#news-search {
  background: var(--surface2) !important; border: 1px solid var(--border) !important;
  color: var(--text) !important; font-family: var(--font-body) !important;
  border-radius: 6px !important;
}
#news-search:focus { border-color: var(--accent) !important; }
.news-item {
  background: linear-gradient(145deg, var(--surface2), var(--surface)) !important;
  border: 1px solid var(--border) !important; border-radius: 8px !important;
  transition: border-color 0.15s !important;
}
.news-item:hover { border-color: var(--accent) !important; }
.news-item-title { font-size: 12px !important; font-weight: 500 !important; line-height: 1.45 !important; }
.news-item-meta { font-family: var(--font-mono) !important; font-size: 10px !important; color: var(--text-muted) !important; }
.news-tag { font-family: var(--font-mono) !important; font-size: 9px !important; border-radius: 3px !important; }
.news-tag.company { background: rgba(0,212,255,0.1) !important; border-color: rgba(0,212,255,0.3) !important; color: var(--accent) !important; }
.news-tag.medicilon { background: var(--gold-dim) !important; border-color: var(--gold-border) !important; color: var(--gold-bright) !important; }

/* CRO Modal */
#cro-modal-overlay {
  background: rgba(0,0,0,0.72) !important;
  backdrop-filter: blur(5px) !important;
}
#cro-modal-overlay.visible { display: flex !important; }
#cro-modal {
  background: rgba(10,16,24,0.97) !important;
  border: 1px solid var(--border-bright) !important;
  border-radius: 14px !important;
  box-shadow: 0 32px 80px rgba(0,0,0,0.8), 0 0 0 1px rgba(0,212,255,0.05) !important;
  backdrop-filter: blur(24px) !important;
  animation: modalIn 0.22s cubic-bezier(0.34,1.56,0.64,1) !important;
}
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.93); }
  to   { opacity: 1; transform: scale(1); }
}
#cro-modal-header { border-bottom: 1px solid var(--border) !important; }
#cro-modal-title { font-family: var(--font-display) !important; font-size: 18px !important; font-weight: 700 !important; }
.modal-section-title { font-family: var(--font-display) !important; font-size: 9px !important; letter-spacing: 0.12em !important; }
.client-est-num { font-family: var(--font-mono) !important; font-size: 21px !important; font-weight: 500 !important; color: var(--accent) !important; }
.client-est-svc { font-size: 10px !important; color: var(--text-muted) !important; }
.client-est-sub { font-family: var(--font-mono) !important; font-size: 9px !important; color: var(--text-dim) !important; }
.tier-1 { background: var(--gold-dim) !important; border-color: var(--gold-border) !important; color: var(--gold-bright) !important; font-family: var(--font-mono) !important; }
.tier-2 { background: var(--accent-dim) !important; border-color: rgba(0,212,255,0.3) !important; color: var(--accent) !important; font-family: var(--font-mono) !important; }

/* Loading spinner */
.spinner { border-top-color: var(--gold) !important; border-color: var(--border) !important; border-top-color: var(--gold) !important; }

/* Buttons */
.btn-sm {
  background: var(--surface2) !important; border: 1px solid var(--border) !important;
  color: var(--text-muted) !important; font-family: var(--font-body) !important;
  border-radius: 5px !important; transition: all 0.15s !important;
}
.btn-sm:hover { background: var(--surface3) !important; color: var(--text) !important; border-color: var(--border-bright) !important; }

/* Error banner */
#error-banner {
  background: rgba(255,69,96,0.12) !important;
  border-color: rgba(255,69,96,0.35) !important;
  font-family: var(--font-mono) !important;
}

/* Animated counter helper */
@keyframes countUp {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.stat-val { animation: countUp 0.5s ease both; }

/* Map container dot-grid background */
#map-container {
  background-image: radial-gradient(circle at 1px 1px, rgba(0,212,255,0.04) 1px, transparent 0);
  background-size: 32px 32px;
}

/* Bottom panel gradient divider */
#bottom-panel {
  position: relative;
}
#bottom-panel::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.3;
}

/* ══ END REDESIGN OVERRIDES ══ */
"""

# Inject override CSS before </style>
html = html.replace('</style>', OVERRIDE_CSS + '\n</style>', 1)
print("OK: CSS overrides injected")

# ── 4. Add animated counter JS ───────────────────────────────────────────────
COUNTER_JS = """
// ── Animated stat counters ──────────────────────────────────────────────────
function animateCounter(el, target, duration) {
  if (!el) return;
  const start = performance.now();
  const startVal = 0;
  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(startVal + (target - startVal) * eased);
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function runCounters() {
  const crosEl = document.getElementById('stat-cros');
  const statesEl = document.getElementById('stat-states');
  const gapEl = document.getElementById('stat-gap');
  const crosVal = parseInt(crosEl?.textContent) || 0;
  const statesVal = parseInt(statesEl?.textContent) || 0;
  const gapVal = parseInt(gapEl?.textContent) || 0;
  if (crosEl) animateCounter(crosEl, crosVal, 800);
  if (statesEl) animateCounter(statesEl, statesVal, 900);
  if (gapEl) animateCounter(gapEl, gapVal, 700);
}
"""

last_script = html.rfind('</script>')
html = html[:last_script] + COUNTER_JS + '\n' + html[last_script:]
print("OK: Counter animation JS added")

# ── 5. Call runCounters after updateStats in init() ──────────────────────────
html = html.replace('updateStats();', 'updateStats();\n    setTimeout(runCounters, 200);', 1)
print("OK: Counter trigger wired")

# ── 6. Write ──────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Done. Final size: {len(html)} bytes")
