import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

original_len = len(html)
changes = []

# ── Fix 1: News close button — toggle -> remove visible ──────────────────────
OLD_CLOSE = (
    "  document.getElementById('news-close-btn').addEventListener('click',()=>{\n"
    "    const panel = document.getElementById('news-panel');\n"
    "    panel.classList.toggle('visible');\n"
    "    if (panel.classList.contains('visible')) {\n"
    "      panel.classList.remove('minimized');\n"
    "      if (NEWS_DATA.length === 0) { loadNewsData().catch(e=>console.warn('[News] load failed:',e)); } else { try{renderNewsList();}catch(e){console.warn('[News] render failed:',e);} }\n"
    "    }\n"
    "  });"
)
NEW_CLOSE = (
    "  document.getElementById('news-close-btn').addEventListener('click',()=>{\n"
    "    document.getElementById('news-panel').classList.remove('visible');\n"
    "  });"
)
if OLD_CLOSE in html:
    html = html.replace(OLD_CLOSE, NEW_CLOSE, 1)
    changes.append("Fix 1: news close button now removes visible (not toggle)")
else:
    changes.append("WARNING Fix 1: close button pattern not found")

# ── Fix 2: Last renderNews() -> renderNewsList() (line 1629) ─────────────────
remaining = html.count('renderNews)')
if remaining:
    html = html.replace('renderNews)', 'renderNewsList)')
    changes.append(f"Fix 2: fixed {remaining} remaining renderNews() calls")

# ── Fix 3: openNewsPanel — toggle open properly ──────────────────────────────
# Find openNewsPanel function
old_open = "document.getElementById('news-open-btn').addEventListener('click',openNewsPanel);"
if old_open in html:
    # Check if openNewsPanel is defined
    if 'function openNewsPanel' not in html:
        OPEN_PANEL_FN = (
            "\nfunction openNewsPanel(){\n"
            "  const panel=document.getElementById('news-panel');\n"
            "  panel.classList.toggle('visible');\n"
            "  if(panel.classList.contains('visible')){\n"
            "    panel.classList.remove('minimized');\n"
            "    if(NEWS_DATA.length===0){loadNewsData().catch(e=>console.warn('[News]',e));}\n"
            "    else{try{renderNewsList();}catch(e){console.warn('[News] render:',e);}}\n"
            "  }\n"
            "}\n"
        )
        html = html.replace('function setupNewsPanel(){', OPEN_PANEL_FN + 'function setupNewsPanel(){', 1)
        changes.append("Fix 3: added openNewsPanel() function")
    else:
        changes.append("Fix 3: openNewsPanel already defined")

# ── Fix 4: Populate compare selectors + wire side-by-side compare ─────────────
# Replace our openCompare() with a proper implementation that:
# 1. Populates the two CRO dropdowns
# 2. Renders a side-by-side comparison when both are selected

OLD_OPEN_COMPARE = '''// ─── Compare Modal ────────────────────────────────────────────────────────────
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
}'''

NEW_OPEN_COMPARE = '''// ─── Compare Modal ────────────────────────────────────────────────────────────
function openCompare() {
  const overlay = document.getElementById('compare-modal-overlay');
  if (!overlay || !croData) return;

  // Populate both selector dropdowns with all CROs
  const selects = document.querySelectorAll('.compare-select-input');
  if (selects.length >= 2) {
    const cros = croData.cros || [];
    selects.forEach((sel, idx) => {
      const current = sel.value;
      sel.innerHTML = '<option value="">— Select CRO —</option>';
      cros.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = (c.is_medicilon ? '⭐ ' : '') + c.short_name;
        sel.appendChild(opt);
      });
      // Default: first selector = Medicilon, second = first competitor
      if (!current) {
        if (idx === 0) {
          const med = cros.find(c => c.is_medicilon);
          if (med) sel.value = med.id;
        } else if (idx === 1) {
          const first = cros.find(c => !c.is_medicilon);
          if (first) sel.value = first.id;
        }
      } else {
        sel.value = current;
      }
    });
    selects.forEach(sel => {
      sel.onchange = renderCompareTable;
    });
  }

  overlay.classList.add('visible');
  renderCompareTable();
}

function renderCompareTable() {
  const body = document.getElementById('compare-modal-body');
  if (!body || !croData) return;

  const selects = document.querySelectorAll('.compare-select-input');
  const ids = Array.from(selects).map(s => s.value).filter(Boolean);
  const cros = ids.map(id => croData.cros.find(c => c.id === id)).filter(Boolean);
  const services = croData.service_categories || [];

  if (cros.length === 0) {
    body.innerHTML = '<div style="padding:24px;color:var(--text-dim);text-align:center">Select CROs above to compare</div>';
    return;
  }

  // Build comparison table
  let html = '<table class="compare-table"><thead><tr><th>Service</th>';
  cros.forEach(c => {
    html += `<th style="color:${c.is_medicilon ? 'var(--gold)' : 'var(--accent)'}">${c.is_medicilon ? '⭐ ' : ''}${c.short_name}<br><small style="color:var(--text-dim);font-weight:400">${(c.states||[]).length} US states</small></th>`;
  });
  html += '</tr></thead><tbody>';

  services.forEach((svc, i) => {
    const bg = i % 2 === 0 ? '' : 'style="background:rgba(255,255,255,0.02)"';
    html += `<tr ${bg}><td class="compare-cro-name">${svc}</td>`;
    cros.forEach(c => {
      const has = (c.services || []).includes(svc);
      html += `<td class="compare-cell ${has ? 'has-service' : 'no-service'}">${has ? '&#10003;' : '&#8212;'}</td>`;
    });
    html += '</tr>';
  });

  // States row
  html += '<tr style="border-top:2px solid var(--border)"><td class="compare-cro-name" style="color:var(--text-muted)">US States</td>';
  cros.forEach(c => {
    const states = c.states || [];
    html += `<td style="font-size:10px;color:var(--text-dim);text-align:center">${states.length > 0 ? states.join(', ') : 'China-based'}</td>`;
  });
  html += '</tr></tbody></table>';

  body.innerHTML = html;
}

function closeCompare() {
  const overlay = document.getElementById('compare-modal-overlay');
  if (overlay) overlay.classList.remove('visible');
}'''

if OLD_OPEN_COMPARE in html:
    html = html.replace(OLD_OPEN_COMPARE, NEW_OPEN_COMPARE, 1)
    changes.append("Fix 4: replaced openCompare() with full implementation (dropdown populate + side-by-side table)")
else:
    changes.append("WARNING Fix 4: openCompare pattern not found — trying partial match")
    if 'function openCompare()' in html:
        changes.append("  openCompare() exists but pattern mismatch — manual check needed")

# ── Write ─────────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"index.html: {original_len:,} -> {len(html):,} bytes\n")
for c in changes:
    print(f"  {'!!' if 'WARNING' in c else 'OK'} {c}")
