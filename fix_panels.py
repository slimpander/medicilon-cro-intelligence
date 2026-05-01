import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

original_len = len(html)
changes = []

# ── Fix 1: renderNews() -> renderNewsList() (function name mismatch) ──────────
count = html.count('renderNews()')
if count:
    html = html.replace('renderNews()', 'renderNewsList()')
    changes.append(f"Fix 1: renamed {count}x renderNews() -> renderNewsList()")
else:
    changes.append("Fix 1: renderNews() not found (already correct)")

# ── Fix 2: Add openCompare + closeCompare functions ───────────────────────────
COMPARE_JS = r"""
// ─── Compare Modal ────────────────────────────────────────────────────────────
function openCompare() {
  const overlay = document.getElementById('compare-modal-overlay');
  if (!overlay) return;
  // Build compare table from current croData
  const cros = (croData && croData.cros) ? croData.cros.filter(c => !c.is_medicilon) : [];
  const medicilon = croData && croData.cros ? croData.cros.find(c => c.is_medicilon) : null;
  const services = (croData && croData.service_categories) ? croData.service_categories : [];

  let tableHtml = '<table class="compare-table"><thead><tr><th>CRO</th>';
  services.forEach(s => { tableHtml += `<th>${s.replace(' / ',' /<br>')}</th>`; });
  tableHtml += '</tr></thead><tbody>';

  const allCros = medicilon ? [medicilon, ...cros] : cros;
  allCros.forEach(cro => {
    const isMed = cro.is_medicilon;
    tableHtml += `<tr class="${isMed ? 'medicilon-row' : ''}">`;
    tableHtml += `<td class="compare-cro-name">${isMed ? '⭐ ' : ''}${cro.short_name}</td>`;
    services.forEach(s => {
      const has = cro.services && cro.services.includes(s);
      tableHtml += `<td class="compare-cell ${has ? 'has-service' : 'no-service'}">${has ? '✓' : '—'}</td>`;
    });
    tableHtml += '</tr>';
  });
  tableHtml += '</tbody></table>';

  const body = document.getElementById('compare-modal-body');
  if (body) body.innerHTML = tableHtml;
  overlay.classList.add('visible');
}

function closeCompare() {
  const overlay = document.getElementById('compare-modal-overlay');
  if (overlay) overlay.classList.remove('visible');
}
"""

# ── Fix 3: Add exportReport function ─────────────────────────────────────────
EXPORT_JS = r"""
// ─── Export ───────────────────────────────────────────────────────────────────
function exportReport(format) {
  // Hide dropdown
  const dd = document.getElementById('export-dropdown');
  if (dd) dd.style.display = 'none';

  if (format === 'png') {
    if (typeof html2canvas === 'undefined') {
      alert('html2canvas not loaded — check CDN connection');
      return;
    }
    html2canvas(document.body, { backgroundColor: '#0a1018', scale: 1.5 }).then(canvas => {
      const a = document.createElement('a');
      a.download = 'CRO-Market-Intelligence-' + new Date().toISOString().slice(0,10) + '.png';
      a.href = canvas.toDataURL('image/png');
      a.click();
    });

  } else if (format === 'csv') {
    if (!croData) { alert('No data loaded'); return; }
    const services = croData.service_categories || [];
    const rows = [['CRO', 'Tier', 'States', ...services]];
    croData.cros.forEach(c => {
      rows.push([
        c.short_name,
        c.is_medicilon ? 'Medicilon' : `Tier ${c.tier}`,
        (c.states || []).join(';'),
        ...services.map(s => (c.services || []).includes(s) ? 'Yes' : 'No')
      ]);
    });
    const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.download = 'CRO-Market-Intelligence-' + new Date().toISOString().slice(0,10) + '.csv';
    a.href = URL.createObjectURL(blob);
    a.click();

  } else if (format === 'json') {
    if (!croData) { alert('No data loaded'); return; }
    const blob = new Blob([JSON.stringify(croData, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.download = 'CRO-Market-Intelligence-' + new Date().toISOString().slice(0,10) + '.json';
    a.href = URL.createObjectURL(blob);
    a.click();
  }
}

function toggleExportDropdown() {
  const dd = document.getElementById('export-dropdown');
  if (!dd) return;
  dd.style.display = dd.style.display === 'block' ? 'none' : 'block';
}

// Close export dropdown when clicking outside
document.addEventListener('click', e => {
  const btn = document.getElementById('export-btn');
  const dd = document.getElementById('export-dropdown');
  if (dd && btn && !btn.contains(e.target) && !dd.contains(e.target)) {
    dd.style.display = 'none';
  }
});
"""

# ── Compare modal CSS additions ───────────────────────────────────────────────
COMPARE_CSS = """
/* ── Compare table ───────────────────────────────────── */
.compare-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.compare-table th { background: var(--surface2); padding: 6px 8px; text-align: center;
  border: 1px solid var(--border); color: var(--text-muted); font-weight: 600;
  position: sticky; top: 0; z-index: 1; }
.compare-table th:first-child { text-align: left; min-width: 130px; }
.compare-table td { padding: 5px 8px; border: 1px solid var(--border); text-align: center; }
.compare-cro-name { text-align: left !important; font-weight: 500; white-space: nowrap; }
.has-service { color: #2ecc71; font-weight: 700; }
.no-service { color: var(--text-dim); }
.medicilon-row td { background: var(--gold-dim); border-color: var(--gold-border); }
#compare-modal { max-width: 95vw; max-height: 85vh; overflow: auto; padding: 24px; }
#compare-modal-body { overflow: auto; max-height: 70vh; }
#compare-modal h2 { margin: 0 0 16px; font-size: 16px; color: var(--text); }
#compare-close-btn { float: right; background: none; border: none; color: var(--text-muted);
  font-size: 20px; cursor: pointer; padding: 0 4px; }
#compare-close-btn:hover { color: var(--text); }

/* ── Export dropdown ─────────────────────────────────── */
#export-dropdown { display: none; position: absolute; top: 100%; right: 0; margin-top: 4px;
  background: var(--surface2); border: 1px solid var(--border); border-radius: 6px;
  min-width: 140px; z-index: 100; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
#export-dropdown button { display: block; width: 100%; background: none; border: none;
  color: var(--text); padding: 8px 14px; text-align: left; font-size: 12px;
  cursor: pointer; font-family: var(--font-body); transition: background 0.15s; }
#export-dropdown button:hover { background: var(--surface3); color: var(--accent); }
"""

# Insert CSS before </style>
if '#compare-modal-body' not in html:
    html = html.replace('</style>', COMPARE_CSS + '\n</style>', 1)
    changes.append("Fix 2a: added compare table + export dropdown CSS")
else:
    changes.append("Fix 2a: compare CSS already present")

# Insert JS functions before init()
INSERT_BEFORE = 'async function init(){'
if 'function openCompare' not in html:
    html = html.replace(INSERT_BEFORE, COMPARE_JS + '\n' + EXPORT_JS + '\n' + INSERT_BEFORE, 1)
    changes.append("Fix 2b: added openCompare/closeCompare/exportReport/toggleExportDropdown functions")
else:
    changes.append("Fix 2b: openCompare already present")

# ── Fix 4: Wire up compare-btn and export-btn in the HTML ────────────────────
# Find compare-btn and wire onclick
OLD_COMPARE_BTN = 'id="compare-btn"'
if OLD_COMPARE_BTN in html and 'onclick="openCompare' not in html:
    html = html.replace(
        '<button id="compare-btn"',
        '<button id="compare-btn" onclick="openCompare()"',
        1
    )
    changes.append("Fix 3a: wired compare-btn onclick -> openCompare()")

# Wire export-btn
OLD_EXPORT_BTN = '<button id="export-btn"'
if OLD_EXPORT_BTN in html and 'onclick="toggleExportDropdown' not in html:
    html = html.replace(
        '<button id="export-btn"',
        '<button id="export-btn" onclick="toggleExportDropdown()"',
        1
    )
    changes.append("Fix 3b: wired export-btn onclick -> toggleExportDropdown()")

# ── Fix 5: Ensure compare modal has close button and body div ─────────────────
# Check if compare-modal-body exists
if 'compare-modal-body' not in html:
    OLD_COMPARE_MODAL = '<div id="compare-modal">'
    NEW_COMPARE_MODAL = '''<div id="compare-modal">
    <h2>CRO Service Comparison <button id="compare-close-btn" onclick="closeCompare()">&#x2715;</button></h2>
    <div id="compare-modal-body"></div>'''
    if OLD_COMPARE_MODAL in html:
        html = html.replace(OLD_COMPARE_MODAL, NEW_COMPARE_MODAL, 1)
        changes.append("Fix 4a: added compare-modal-body and close button")

# ── Fix 6: Add export dropdown HTML next to export-btn ───────────────────────
if 'export-dropdown' not in html:
    # Find the export-btn and add dropdown after its closing tag
    # Look for pattern: <button id="export-btn"...>...</button>
    m = re.search(r'<button[^>]*id="export-btn"[^>]*>.*?</button>', html, re.DOTALL)
    if m:
        OLD_BTN = m.group(0)
        # Wrap in a relative div with dropdown
        NEW_BTN = (
            '<div style="position:relative;display:inline-block">'
            + OLD_BTN +
            '<div id="export-dropdown">'
            '<button onclick="exportReport(\'png\')">📸 Export PNG</button>'
            '<button onclick="exportReport(\'csv\')">📊 Export CSV</button>'
            '<button onclick="exportReport(\'json\')">📄 Export JSON</button>'
            '</div></div>'
        )
        html = html.replace(OLD_BTN, NEW_BTN, 1)
        changes.append("Fix 4b: added export dropdown HTML")
    else:
        changes.append("WARNING Fix 4b: export-btn not found in HTML")
else:
    changes.append("Fix 4b: export-dropdown already present")

# ── Fix 7: Close compare modal on overlay click ───────────────────────────────
OLD_OVERLAY = 'id="compare-modal-overlay"'
if OLD_OVERLAY in html and 'onclick="closeCompare' not in html:
    html = html.replace(
        '<div id="compare-modal-overlay">',
        '<div id="compare-modal-overlay" onclick="if(event.target===this)closeCompare()">',
        1
    )
    changes.append("Fix 5: compare overlay click-outside to close")

# ── Write ─────────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"index.html: {original_len:,} -> {len(html):,} bytes")
print()
for c in changes:
    print(f"  {'OK' if 'WARNING' not in c else '!!'} {c}")
