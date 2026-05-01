"""
add_features.py — Add Timeline tab, Compare modal, Export button, City dots, Market $ estimates.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

print(f"Starting: {len(html)} bytes")

# ═══════════════════════════════════════════════════════════════════════════════
# PART A: CSS for new features
# ═══════════════════════════════════════════════════════════════════════════════
NEW_FEATURE_CSS = """
/* ── Timeline Tab ────────────────────────────────────── */
#tab-timeline {
  padding: 14px 20px; overflow-x: auto; overflow-y: hidden;
  display: none; flex-direction: column; gap: 10px;
}
#tab-timeline.active { display: flex; }
.timeline-container {
  display: flex; flex-direction: column; gap: 6px; min-width: 700px;
}
.timeline-header {
  display: flex; align-items: center; gap: 0;
  padding-left: 160px; margin-bottom: 4px;
}
.timeline-year-label {
  font-family: var(--font-mono); font-size: 9px; color: var(--text-dim);
  flex: 1; text-align: center; min-width: 40px;
}
.timeline-row {
  display: flex; align-items: center; gap: 10px; height: 26px;
}
.timeline-company-name {
  width: 150px; font-size: 11px; font-weight: 500; color: var(--text-muted);
  flex-shrink: 0; text-align: right; padding-right: 10px;
  font-family: var(--font-body);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.timeline-company-name.medicilon { color: var(--gold); font-weight: 600; }
.timeline-track {
  flex: 1; height: 16px; position: relative;
  background: var(--surface2); border-radius: 3px; overflow: visible;
}
.timeline-bar {
  position: absolute; top: 0; height: 100%; border-radius: 3px;
  transition: opacity 0.2s;
}
.timeline-bar:hover { opacity: 0.85; }
.timeline-entry-marker {
  position: absolute; top: -3px;
  width: 22px; height: 22px;
  background: var(--gold);
  clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
  box-shadow: 0 0 10px var(--gold-glow);
  cursor: pointer;
}
.timeline-entry-label {
  position: absolute; top: -18px;
  font-size: 9px; color: var(--gold);
  font-family: var(--font-mono); white-space: nowrap;
}

/* ── Compare Modal ───────────────────────────────────── */
#compare-modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.75);
  z-index: 300; display: none; align-items: center; justify-content: center;
  backdrop-filter: blur(5px);
}
#compare-modal-overlay.visible { display: flex; }
#compare-modal {
  background: rgba(10,16,24,0.97);
  border: 1px solid var(--border-bright); border-radius: 14px;
  width: 760px; max-width: 94vw; max-height: 85vh;
  display: flex; flex-direction: column;
  box-shadow: 0 32px 80px rgba(0,0,0,0.8);
  backdrop-filter: blur(24px);
  animation: modalIn 0.22s cubic-bezier(0.34,1.56,0.64,1);
  overflow: hidden;
}
#compare-header {
  display: flex; align-items: center; padding: 16px 20px;
  border-bottom: 1px solid var(--border); gap: 12px; flex-shrink: 0;
}
#compare-header h2 { font-family: var(--font-display); font-size: 17px; font-weight: 700; flex: 1; }
.compare-close-btn {
  background: none; border: none; color: var(--text-dim); cursor: pointer;
  font-size: 18px; padding: 2px 6px; border-radius: 4px; font-family: inherit;
  transition: all 0.15s;
}
.compare-close-btn:hover { color: var(--text); background: var(--surface2); }
#compare-selectors {
  display: flex; gap: 12px; padding: 14px 20px; border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.compare-selector {
  flex: 1; display: flex; flex-direction: column; gap: 6px;
}
.compare-selector label { font-size: 10px; font-weight: 600; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.1em; font-family: var(--font-display); }
.compare-select-input {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 8px 10px; color: var(--text);
  font-size: 12px; font-family: var(--font-body); outline: none; cursor: pointer;
}
.compare-select-input:focus { border-color: var(--accent); }
.compare-vs-badge {
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 12px; font-weight: 700;
  color: var(--text-dim); padding-top: 22px;
}
#compare-body {
  flex: 1; overflow-y: auto; padding: 16px 20px;
  display: grid; grid-template-columns: 1fr auto 1fr; gap: 12px;
}
.compare-col { display: flex; flex-direction: column; gap: 8px; }
.compare-col-header { font-family: var(--font-display); font-size: 15px; font-weight: 700; padding-bottom: 8px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px; }
.compare-divider { width: 1px; background: var(--border); margin: 0 4px; }
.compare-section-title { font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim); font-family: var(--font-display); margin-top: 8px; margin-bottom: 4px; }
.compare-svc-row { display: flex; align-items: center; gap: 6px; padding: 3px 0; font-size: 11px; }
.compare-svc-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.compare-svc-present { color: var(--green); }
.compare-svc-absent { color: var(--text-dim); text-decoration: line-through; }
.compare-svc-unique { color: var(--gold); font-weight: 600; }
.compare-stat { font-family: var(--font-mono); font-size: 20px; font-weight: 500; color: var(--accent); }
.compare-stat-label { font-size: 10px; color: var(--text-muted); }
.compare-preset-btns { display: flex; gap: 6px; padding: 0 20px 14px; flex-shrink: 0; }
.compare-preset {
  padding: 5px 12px; border-radius: 20px; font-size: 11px; cursor: pointer;
  background: var(--surface2); border: 1px solid var(--border);
  color: var(--text-muted); font-family: var(--font-body); transition: all 0.15s;
}
.compare-preset:hover { border-color: var(--gold-border); color: var(--gold); background: var(--gold-dim); }

/* ── Export dropdown ─────────────────────────────────── */
#export-btn {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 6px 14px; color: var(--text);
  font-size: 12px; cursor: pointer; font-family: var(--font-body);
  font-weight: 500; transition: all 0.15s;
  display: flex; align-items: center; gap: 5px; position: relative;
}
#export-btn:hover { border-color: var(--accent); color: var(--accent); }
#compare-btn {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 6px 14px; color: var(--text);
  font-size: 12px; cursor: pointer; font-family: var(--font-body);
  font-weight: 500; transition: all 0.15s;
  display: flex; align-items: center; gap: 5px;
}
#compare-btn:hover { border-color: var(--accent); color: var(--accent); }
#export-dropdown {
  position: absolute; top: 100%; right: 0; margin-top: 4px;
  background: var(--surface); border: 1px solid var(--border-bright);
  border-radius: 8px; padding: 4px; z-index: 500;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5); display: none; min-width: 160px;
}
#export-dropdown.visible { display: block; }
.export-option {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px;
  border-radius: 5px; cursor: pointer; font-size: 12px;
  color: var(--text-muted); transition: all 0.15s; font-family: var(--font-body);
}
.export-option:hover { background: var(--surface2); color: var(--text); }

/* City dots on map */
.city-dot {
  fill: var(--gold); stroke: rgba(240,165,0,0.4); stroke-width: 1.5;
  cursor: pointer; transition: all 0.2s;
}
.city-dot:hover { fill: var(--gold-bright); r: 6; filter: drop-shadow(0 0 4px var(--gold-glow)); }
"""

html = html.replace('</style>', NEW_FEATURE_CSS + '\n</style>', 1)
print("OK: Feature CSS added")

# ═══════════════════════════════════════════════════════════════════════════════
# PART B: HTML additions
# ═══════════════════════════════════════════════════════════════════════════════

# 1. Add Compare + Export buttons in topbar (before news-open-btn)
old_news_btn = '<button id="news-open-btn">'
new_topbar_btns = '''<div style="position:relative">
    <button id="export-btn">📤 Export <span style="font-size:9px;opacity:0.6">▾</span>
      <div id="export-dropdown">
        <div class="export-option" id="export-png-btn">🖼️ Save as PNG</div>
        <div class="export-option" id="export-pdf-btn">📄 Print / PDF</div>
        <div class="export-option" id="export-copy-btn">📋 Copy Summary</div>
      </div>
    </button>
  </div>
  <button id="compare-btn">⚔️ Compare</button>
  <button id="news-open-btn">'''
if old_news_btn in html:
    html = html.replace(old_news_btn, new_topbar_btns, 1)
    print("OK: Compare + Export buttons added to topbar")
else:
    print("WARNING: news-open-btn not found in topbar")

# 2. Add Timeline tab button
if 'data-tab="strategy"' in html:
    html = html.replace(
        'data-tab="strategy"',
        'data-tab="strategy"',
        1
    )
    # Find strategy tab button and add timeline after
    idx = html.find('data-tab="strategy"')
    end = html.find('</button>', idx) + 9
    html = html[:end] + '\n        <button class="tab-btn" data-tab="timeline">🕐 Timeline</button>' + html[end:]
    print("OK: Timeline tab button added")

# 3. Add Timeline tab pane
if 'id="tab-timeline"' not in html:
    if 'id="tab-strategy"' in html:
        idx = html.find('id="tab-strategy"')
        end = html.find('>', idx) + 1
        html = html[:end] + '\n        <div class="tab-pane" id="tab-timeline"></div>' + html[end:]
        print("OK: Timeline tab pane added")

# 4. Add Compare modal before </body>
COMPARE_MODAL = '''
<!-- Compare Modal -->
<div id="compare-modal-overlay">
  <div id="compare-modal">
    <div id="compare-header">
      <h2>⚔️ CRO Comparison</h2>
      <button class="compare-close-btn" id="compare-close">✕</button>
    </div>
    <div id="compare-selectors">
      <div class="compare-selector">
        <label>Company A</label>
        <select class="compare-select-input" id="compare-a"></select>
      </div>
      <div class="compare-vs-badge">VS</div>
      <div class="compare-selector">
        <label>Company B</label>
        <select class="compare-select-input" id="compare-b"></select>
      </div>
    </div>
    <div class="compare-preset-btns">
      <button class="compare-preset" data-a="medicilon" data-b="charles_river">vs Charles River</button>
      <button class="compare-preset" data-a="medicilon" data-b="wuxi">vs WuXi AppTec</button>
      <button class="compare-preset" data-a="medicilon" data-b="pharmaron">vs Pharmaron</button>
      <button class="compare-preset" data-a="medicilon" data-b="covance">vs Covance</button>
    </div>
    <div id="compare-body"></div>
  </div>
</div>
'''
html = html.replace('<!-- CRO Company Profile Modal -->', COMPARE_MODAL + '\n<!-- CRO Company Profile Modal -->', 1)
print("OK: Compare modal HTML added")

# ═══════════════════════════════════════════════════════════════════════════════
# PART C: JavaScript
# ═══════════════════════════════════════════════════════════════════════════════
FEATURE_JS = r"""
// ─── Market Size Data ─────────────────────────────────────────────────────────
const MARKET_USD = {
  'In Vivo / Mouse Services': '$2.1B',
  'DMPK': '$3.4B',
  'ADME': '$2.8B',
  'Toxicology': '$4.2B',
  'Bioanalysis': '$5.1B',
  'CMC': '$8.3B',
  'Clinical Trials': '$52B',
  'Regulatory Affairs': '$1.8B',
  'Biomarker / Genomics': '$3.9B',
  'Protein Sciences / Biologics': '$6.7B'
};

// ─── CRO US Entry Timeline Data ───────────────────────────────────────────────
const CRO_TIMELINE = {
  'charles_river':  { start: 1947, peak: 1980, label: 'Charles River' },
  'covance':        { start: 1968, peak: 1980, label: 'Covance/Labcorp' },
  'icon':           { start: 1995, peak: 2000, label: 'ICON plc' },
  'syneos':         { start: 2000, peak: 2010, label: 'Syneos Health' },
  'eurofins':       { start: 2005, peak: 2012, label: 'Eurofins' },
  'bioagilytix':    { start: 2008, peak: 2012, label: 'BioAgilytix' },
  'celerion':       { start: 2011, peak: 2014, label: 'Celerion' },
  'crown_bio':      { start: 2016, peak: 2018, label: 'Crown Bioscience' },
  'pharmaron':      { start: 2017, peak: 2019, label: 'Pharmaron' },
  'wuxi':           { start: 2014, peak: 2016, label: 'WuXi AppTec' },
  'altasciences':   { start: 2019, peak: 2021, label: 'Altasciences' },
  'biotrial':       { start: 2016, peak: 2018, label: 'Biotrial' },
  'medicilon':      { start: 2026, peak: null,  label: 'Medicilon', isTarget: true }
};

// ─── Timeline Render ──────────────────────────────────────────────────────────
function renderTimeline() {
  const pane = document.getElementById('tab-timeline');
  if (!pane || pane.dataset.rendered) return;
  pane.dataset.rendered = '1';

  const MIN_YEAR = 1940, MAX_YEAR = 2030;
  const YEAR_RANGE = MAX_YEAR - MIN_YEAR;
  const STEP = 10;

  // Build year labels
  const container = document.createElement('div');
  container.className = 'timeline-container';

  // Header row
  const header = document.createElement('div');
  header.className = 'timeline-header';
  for (let y = MIN_YEAR; y <= MAX_YEAR; y += STEP) {
    const lbl = document.createElement('div');
    lbl.className = 'timeline-year-label';
    lbl.textContent = y;
    lbl.style.width = (STEP / YEAR_RANGE * 100) + '%';
    lbl.style.flex = 'none';
    header.appendChild(lbl);
  }
  container.appendChild(header);

  // Rows
  const orderedIds = Object.keys(CRO_TIMELINE).sort((a, b) => {
    if (a === 'medicilon') return 1;
    if (b === 'medicilon') return -1;
    return CRO_TIMELINE[a].start - CRO_TIMELINE[b].start;
  });

  orderedIds.forEach(id => {
    const t = CRO_TIMELINE[id];
    const cro = croData.cros.find(c => c.id === id);
    const color = cro ? (croColors[cro.id] || '#3b9eff') : 'var(--gold)';

    const row = document.createElement('div');
    row.className = 'timeline-row';

    const nameDiv = document.createElement('div');
    nameDiv.className = 'timeline-company-name' + (t.isTarget ? ' medicilon' : '');
    nameDiv.textContent = t.label;
    row.appendChild(nameDiv);

    const track = document.createElement('div');
    track.className = 'timeline-track';

    if (t.isTarget) {
      // Diamond marker for Medicilon target entry
      const pct = ((t.start - MIN_YEAR) / YEAR_RANGE * 100);
      const marker = document.createElement('div');
      marker.className = 'timeline-entry-marker';
      marker.style.left = 'calc(' + pct + '% - 11px)';
      const lbl = document.createElement('div');
      lbl.className = 'timeline-entry-label';
      lbl.textContent = t.start + ' target';
      lbl.style.left = 'calc(' + pct + '% - 20px)';
      track.appendChild(lbl);
      track.appendChild(marker);
    } else {
      const startPct = ((t.start - MIN_YEAR) / YEAR_RANGE * 100);
      const bar = document.createElement('div');
      bar.className = 'timeline-bar';
      bar.style.left = startPct + '%';
      bar.style.width = (100 - startPct) + '%';
      bar.style.background = 'linear-gradient(90deg, ' + color + '99, ' + color + 'cc)';
      bar.title = t.label + ' US presence since ' + t.start;
      track.appendChild(bar);
    }

    row.appendChild(track);
    container.appendChild(row);
  });

  pane.appendChild(container);
}

// ─── Compare Modal ────────────────────────────────────────────────────────────
function initCompareModal() {
  const overlay = document.getElementById('compare-modal-overlay');
  if (!overlay) return;

  // Populate selects
  ['compare-a', 'compare-b'].forEach((id, i) => {
    const sel = document.getElementById(id);
    if (!sel) return;
    // Medicilon first in A, competitor in B
    croData.cros.forEach(cro => {
      const opt = document.createElement('option');
      opt.value = cro.id;
      opt.textContent = cro.short_name;
      if (i === 0 && cro.is_medicilon) opt.selected = true;
      if (i === 1 && cro.id === 'charles_river') opt.selected = true;
      sel.appendChild(opt);
    });
    sel.addEventListener('change', updateCompare);
  });

  // Preset buttons
  document.querySelectorAll('.compare-preset').forEach(btn => {
    btn.addEventListener('click', () => {
      const a = btn.dataset.a, b = btn.dataset.b;
      const selA = document.getElementById('compare-a');
      const selB = document.getElementById('compare-b');
      if (selA) selA.value = a;
      if (selB) selB.value = b;
      updateCompare();
    });
  });

  document.getElementById('compare-btn')?.addEventListener('click', () => {
    overlay.classList.add('visible');
    updateCompare();
  });
  document.getElementById('compare-close')?.addEventListener('click', () => overlay.classList.remove('visible'));
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.classList.remove('visible'); });
}

function updateCompare() {
  const aId = document.getElementById('compare-a')?.value;
  const bId = document.getElementById('compare-b')?.value;
  if (!aId || !bId) return;
  const croA = croData.cros.find(c => c.id === aId);
  const croB = croData.cros.find(c => c.id === bId);
  if (!croA || !croB) return;

  const body = document.getElementById('compare-body');
  if (!body) return;

  const allSvcs = croData.service_categories || [];
  const aSet = new Set(croA.services || []);
  const bSet = new Set(croB.services || []);
  const aOnly = allSvcs.filter(s => aSet.has(s) && !bSet.has(s));
  const bOnly = allSvcs.filter(s => bSet.has(s) && !aSet.has(s));
  const both  = allSvcs.filter(s => aSet.has(s) && bSet.has(s));

  const aClients = estimateClients(croA);
  const bClients = estimateClients(croB);
  const aTotalClients = Object.values(aClients).reduce((s,v) => s+v.est, 0);
  const bTotalClients = Object.values(bClients).reduce((s,v) => s+v.est, 0);

  function buildCol(cro, otherCro, isA) {
    const otherSet = new Set(otherCro.services || []);
    const color = croColors[cro.id] || '#888';
    const clients = estimateClients(cro);
    const totalC = Object.values(clients).reduce((s,v) => s+v.est, 0);
    let h = '<div class="compare-col">';
    h += '<div class="compare-col-header"><div style="width:12px;height:12px;border-radius:50%;background:' + color + ';flex-shrink:0"></div>' + cro.name + (cro.is_medicilon ? ' <span style="font-size:10px;color:var(--gold)">★ Our Company</span>' : '') + '</div>';

    // Stats
    h += '<div class="compare-section-title">Overview</div>';
    h += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">';
    h += '<div><div class="compare-stat">' + (cro.states||[]).length + '</div><div class="compare-stat-label">US States</div></div>';
    h += '<div><div class="compare-stat" style="font-size:16px">~' + totalC + '</div><div class="compare-stat-label">Est. Clients/yr</div></div>';
    const tierNames = {1:'Tier 1',2:'Tier 2',3:'Tier 3'};
    h += '<div><div class="compare-stat" style="font-size:14px">' + (tierNames[cro.tier]||'—') + '</div><div class="compare-stat-label">Market Tier</div></div>';
    h += '</div>';

    // Services
    h += '<div class="compare-section-title">Services</div>';
    allSvcs.forEach(svc => {
      const has = (cro.services||[]).includes(svc);
      const otherHas = (otherCro.services||[]).includes(svc);
      const unique = has && !otherHas;
      const col = SERVICE_COLORS[svc] || '#888';
      h += '<div class="compare-svc-row">';
      h += '<div class="compare-svc-dot" style="background:' + (has ? col : 'transparent') + ';border:1px solid ' + (has ? col : 'var(--border)') + '"></div>';
      h += '<span class="' + (has ? (unique ? 'compare-svc-unique' : 'compare-svc-present') : 'compare-svc-absent') + '">' + svc;
      if (unique) h += ' ★';
      const mkt = MARKET_USD[svc];
      if (mkt && has) h += ' <span style="font-size:9px;color:var(--text-dim);font-family:var(--font-mono)">' + mkt + '</span>';
      h += '</span></div>';
    });
    h += '</div>';
    return h;
  }

  body.innerHTML = buildCol(croA, croB, true) + '<div class="compare-divider"></div>' + buildCol(croB, croA, false);
}

// ─── Export ───────────────────────────────────────────────────────────────────
function initExport() {
  const btn = document.getElementById('export-btn');
  const dropdown = document.getElementById('export-dropdown');
  if (!btn || !dropdown) return;

  btn.addEventListener('click', e => {
    e.stopPropagation();
    dropdown.classList.toggle('visible');
  });
  document.addEventListener('click', () => dropdown.classList.remove('visible'));

  document.getElementById('export-png-btn')?.addEventListener('click', () => {
    dropdown.classList.remove('visible');
    // Use html2canvas if available
    if (typeof html2canvas !== 'undefined') {
      const target = document.getElementById('map-container');
      html2canvas(target, { backgroundColor: '#080d12', scale: 2 }).then(canvas => {
        const a = document.createElement('a');
        a.download = 'medicilon-cro-map.png';
        a.href = canvas.toDataURL('image/png');
        a.click();
      });
    } else {
      alert('html2canvas not loaded. Try Export PDF instead.');
    }
  });

  document.getElementById('export-pdf-btn')?.addEventListener('click', () => {
    dropdown.classList.remove('visible');
    window.print();
  });

  document.getElementById('export-copy-btn')?.addEventListener('click', () => {
    dropdown.classList.remove('visible');
    const top5 = getTopOpportunityStates(5);
    const med = croData.cros.find(c => c.is_medicilon);
    let md = '# Medicilon US Market Gap Analysis\n\n';
    md += '**Generated:** ' + new Date().toLocaleDateString() + '\n\n';
    md += '## Top Opportunity States\n\n';
    top5.forEach((item, i) => {
      md += (i+1) + '. **' + (STATE_NAMES[item.abbr]||item.abbr) + '** — Score: ' + item.score + '/100\n';
      buildReasons(item).forEach(r => { md += '   - ' + r + '\n'; });
    });
    md += '\n## Medicilon Core Services\n\n';
    (med?.core_services || []).forEach(s => { md += '- ' + s + ' (' + (MARKET_USD[s]||'') + ' market)\n'; });
    navigator.clipboard.writeText(md).then(() => {
      const orig = document.getElementById('export-copy-btn').textContent;
      document.getElementById('export-copy-btn').textContent = '✓ Copied!';
      setTimeout(() => { document.getElementById('export-copy-btn').textContent = orig; }, 2000);
    }).catch(() => alert('Copy failed — use Ctrl+C'));
  });
}

// ─── City Dots on Map ─────────────────────────────────────────────────────────
function renderCityDots(svg, projection, selectedStateAbbr) {
  svg.selectAll('.city-dot').remove();
  svg.selectAll('.city-label').remove();
  if (!selectedStateAbbr) return;

  // Collect all cities in this state
  const cityMap = {};
  croData.cros.forEach(cro => {
    if (cro.is_medicilon) return;
    (cro.cities || []).forEach(c => {
      if (c.state === selectedStateAbbr) {
        const key = c.city + '_' + c.state;
        if (!cityMap[key]) cityMap[key] = { city: c.city, state: c.state, cros: [] };
        cityMap[key].cros.push(cro.short_name);
      }
    });
  });

  // Approximate lat/long for major biotech cities
  const CITY_COORDS = {
    'Wilmington_MA': [42.545, -71.165], 'Boston_MA': [42.36, -71.06],
    'Raleigh_NC': [35.78, -78.64], 'Durham_NC': [35.99, -78.90],
    'Philadelphia_PA': [39.95, -75.17], 'Horsham_PA': [40.18, -75.12],
    'Houston_TX': [29.76, -95.37], 'Austin_TX': [30.27, -97.74], 'Dallas_TX': [32.78, -96.80],
    'San Diego_CA': [32.72, -117.15], 'San Francisco_CA': [37.77, -122.42],
    'Hollister_CA': [36.85, -121.40],
    'Redmond_WA': [47.67, -122.12], 'Everett_WA': [47.98, -122.20],
    'Ann Arbor_MI': [42.28, -83.75], 'Cincinnati_OH': [39.10, -84.51],
    'Madison_WI': [43.07, -89.40], 'Princeton_NJ': [40.36, -74.66],
    'Plainsboro_NJ': [40.33, -74.59], 'Newark_NJ': [40.74, -74.17],
    'Cranbury_NJ': [40.31, -74.51], 'Bridgewater_NJ': [40.60, -74.60],
    'Piscataway_NJ': [40.55, -74.46],
    'Atlanta_GA': [33.75, -84.39], 'St. Paul_MN': [44.95, -93.09],
    'Minneapolis_MN': [44.98, -93.27], 'Lexington_KY': [38.04, -84.50],
    'Baltimore_MD': [39.29, -76.61], 'Denver_CO': [39.74, -104.98],
    'Vienna_VA': [38.90, -77.27], 'Indianapolis_IN': [39.77, -86.16],
    'Lenexa_KS': [38.95, -94.73], 'Lincoln_NE': [40.81, -96.68],
    'Tempe_AZ': [33.42, -111.94], 'Las Vegas_NV': [36.17, -115.14],
    'Portland_OR': [45.52, -122.68], 'Kansas City_MO': [39.10, -94.58],
    'St. Louis_MO': [38.63, -90.20], 'Chicago_IL': [41.88, -87.63],
    'Milwaukee_WI': [43.04, -87.91], 'San Antonio_TX': [29.42, -98.49],
    'New York_NY': [40.71, -74.01], 'Saugerties_NY': [42.07, -73.95],
    'Miami_FL': [25.77, -80.19], 'Tampa_FL': [27.95, -82.46],
    'Lancaster_PA': [40.04, -76.31],
  };

  Object.values(cityMap).forEach(c => {
    const key = c.city + '_' + c.state;
    const coords = CITY_COORDS[key];
    if (!coords) return;
    const [lat, lon] = coords;
    const proj = projection([lon, lat]);
    if (!proj) return;

    const r = Math.min(3 + c.cros.length * 1.5, 8);
    svg.append('circle')
      .attr('class', 'city-dot')
      .attr('cx', proj[0]).attr('cy', proj[1])
      .attr('r', r)
      .attr('title', c.city + ': ' + c.cros.join(', '))
      .on('mousemove', function(event) {
        const tt = document.getElementById('tooltip');
        tt.style.display = 'block';
        tt.style.left = (event.clientX + 12) + 'px';
        tt.style.top = (event.clientY - 20) + 'px';
        tt.innerHTML = '<div class="tt-state">' + c.city + ', ' + c.state + '</div><div class="tt-count">' + c.cros.length + ' CRO' + (c.cros.length !== 1 ? 's' : '') + '</div><div class="tt-companies">' + c.cros.map(n => '<div class="tt-co">' + n + '</div>').join('') + '</div>';
      })
      .on('mouseleave', function() { document.getElementById('tooltip').style.display = 'none'; });
  });
}
"""

last_script = html.rfind('</script>')
html = html[:last_script] + FEATURE_JS + '\n' + html[last_script:]
print("OK: Feature JS added")

# ── Wire timeline tab render ─────────────────────────────────────────────────
old_strategy_hook = "if(btn.dataset.tab==='strategy')renderStrategyPanel();"
new_strategy_hook = "if(btn.dataset.tab==='strategy')renderStrategyPanel();if(btn.dataset.tab==='timeline')renderTimeline();"
if old_strategy_hook in html:
    html = html.replace(old_strategy_hook, new_strategy_hook, 1)
    print("OK: Timeline tab render wired")
else:
    print("WARNING: strategy tab hook not found")

# ── Add html2canvas CDN ──────────────────────────────────────────────────────
old_d3 = '<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>'
new_d3 = old_d3 + '\n<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>'
if old_d3 in html:
    html = html.replace(old_d3, new_d3, 1)
    print("OK: html2canvas CDN added")

# ── Wire compare + export init in init() ────────────────────────────────────
html = html.replace(
    'initNewsPanel();',
    'initNewsPanel();\n    initCompareModal();\n    initExport();',
    1
)
print("OK: Compare + Export init wired")

# ── Write ────────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Done. Final size: {len(html)} bytes")

# Verify
checks = ['renderTimeline', 'compare-modal-overlay', 'export-dropdown',
          'MARKET_USD', 'renderCityDots', 'html2canvas', 'initCompareModal', 'initExport']
for c in checks:
    print(('OK' if c in html else 'MISSING') + '  ' + c)
