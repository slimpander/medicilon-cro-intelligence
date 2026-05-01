"""
patch_v3.py — Add 4 features to index.html:
1. CRO company profile modal (click company in legend)
2. News item hyperlinks
3. Client count estimates
4. Marketing suggestions panel (new bottom tab)
"""
import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

print(f"Starting size: {len(html)} bytes")

# ═══════════════════════════════════════════════════════════════════════════════
# 1. CSS
# ═══════════════════════════════════════════════════════════════════════════════
NEW_CSS = """
/* ── Company Profile Modal ──────────────────────────────── */
#cro-modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  z-index: 300; display: none; align-items: center; justify-content: center;
  backdrop-filter: blur(2px);
}
#cro-modal-overlay.visible { display: flex; }
#cro-modal {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; width: 540px; max-width: 92vw; max-height: 80vh;
  display: flex; flex-direction: column; box-shadow: 0 24px 64px rgba(0,0,0,0.6);
  overflow: hidden;
}
#cro-modal-header {
  padding: 18px 20px 14px; border-bottom: 1px solid var(--border);
  display: flex; align-items: flex-start; gap: 12px;
}
.cro-modal-dot {
  width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; margin-top: 3px;
}
.cro-modal-title { font-size: 17px; font-weight: 700; flex: 1; }
.cro-modal-sub { font-size: 11px; color: var(--text-muted); margin-top: 3px; }
#cro-modal-close {
  background: none; border: none; color: var(--text-dim); cursor: pointer;
  font-size: 18px; padding: 2px 6px; border-radius: 4px; font-family: inherit;
  transition: all 0.15s;
}
#cro-modal-close:hover { color: var(--text); background: var(--surface2); }
#cro-modal-body { flex: 1; overflow-y: auto; padding: 18px 20px; }
#cro-modal-body::-webkit-scrollbar { width: 4px; }
#cro-modal-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
.modal-section { margin-bottom: 18px; }
.modal-section-title {
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--text-dim); margin-bottom: 8px;
}
.modal-kv-grid {
  display: grid; grid-template-columns: 120px 1fr; gap: 5px 10px;
}
.modal-kv-key { font-size: 11px; color: var(--text-muted); }
.modal-kv-val { font-size: 11px; color: var(--text); }
.modal-kv-val a { color: var(--accent); text-decoration: none; }
.modal-kv-val a:hover { text-decoration: underline; }
.modal-services-grid { display: flex; flex-wrap: wrap; gap: 5px; }
.modal-svc-pill {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 20px; font-size: 11px;
  border: 1px solid var(--border); background: var(--surface2);
}
.modal-svc-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.client-estimate-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
}
.client-est-card {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 10px 12px;
}
.client-est-svc { font-size: 10px; color: var(--text-muted); margin-bottom: 4px; }
.client-est-num { font-size: 20px; font-weight: 700; color: var(--accent); }
.client-est-sub { font-size: 9px; color: var(--text-dim); margin-top: 2px; }
.client-est-bar-wrap {
  height: 3px; background: var(--surface3); border-radius: 2px; margin-top: 5px;
}
.client-est-bar { height: 100%; border-radius: 2px; }
.modal-states-list { display: flex; flex-wrap: wrap; gap: 5px; }
.modal-state-tag {
  padding: 2px 8px; border-radius: 3px; font-size: 11px;
  background: var(--surface2); border: 1px solid var(--border); color: var(--text-muted);
  cursor: pointer; transition: all 0.15s;
}
.modal-state-tag:hover { border-color: var(--accent); color: var(--accent); }
.tier-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
}
.tier-1 { background: rgba(245,166,35,0.15); border: 1px solid rgba(245,166,35,0.4); color: var(--gold); }
.tier-2 { background: rgba(59,158,255,0.12); border: 1px solid rgba(59,158,255,0.3); color: var(--accent); }
.tier-3 { background: var(--surface2); border: 1px solid var(--border); color: var(--text-muted); }

/* ── Marketing Panel ─────────────────────────────────────── */
.strategy-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 10px; padding: 14px 20px; height: 100%; overflow-y: auto; box-sizing: border-box;
}
.strategy-card {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px 14px;
}
.strategy-card-icon { font-size: 20px; margin-bottom: 6px; }
.strategy-card-title {
  font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 6px;
}
.strategy-card-body { font-size: 11px; color: var(--text-muted); line-height: 1.6; }
.strategy-card-body ul { padding-left: 14px; margin: 4px 0; }
.strategy-card-body li { margin-bottom: 3px; }
.strategy-highlight {
  background: var(--gold-dim); border: 1px solid var(--gold-border);
  border-radius: 4px; padding: 3px 7px; font-size: 10px;
  color: var(--gold); display: inline-block; margin: 2px 2px 0 0;
}
.strategy-card.full-width { grid-column: 1 / -1; }
"""
html = html.replace('</style>', NEW_CSS + '\n</style>', 1)
print("OK: CSS added")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. HTML — modal overlay + 4th bottom tab
# ═══════════════════════════════════════════════════════════════════════════════

# Add modal overlay before </body>
MODAL_HTML = """
<!-- CRO Company Profile Modal -->
<div id="cro-modal-overlay">
  <div id="cro-modal">
    <div id="cro-modal-header">
      <div class="cro-modal-dot" id="cro-modal-dot"></div>
      <div>
        <div class="cro-modal-title" id="cro-modal-title">—</div>
        <div class="cro-modal-sub" id="cro-modal-sub">—</div>
      </div>
      <button id="cro-modal-close">✕</button>
    </div>
    <div id="cro-modal-body"></div>
  </div>
</div>
"""
html = html.replace('<!-- News Panel -->', MODAL_HTML + '\n<!-- News Panel -->', 1)
print("OK: Modal HTML added")

# Add 4th tab button
html = html.replace(
    '<button class="tab-btn" data-tab="underserved">Underserved States</button>',
    '<button class="tab-btn" data-tab="underserved">Underserved States</button>\n        <button class="tab-btn" data-tab="strategy">📊 Medicilon Strategy</button>',
    1
)
# Add 4th tab pane
html = html.replace(
    '<div class="tab-pane" id="tab-underserved"></div>',
    '<div class="tab-pane" id="tab-underserved"></div>\n        <div class="tab-pane" id="tab-strategy"></div>',
    1
)
print("OK: Strategy tab added")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. JavaScript
# ═══════════════════════════════════════════════════════════════════════════════

NEW_JS = r"""
// ─── Client Estimate Model ────────────────────────────────────────────────────
// Estimated annual clients per service based on company tier, footprint, market data proxies
const MARKET_SIZE = {
  'In Vivo / Mouse Services': { total: 1200, desc: 'est. annual studies across US CROs' },
  'DMPK':                     { total: 2800, desc: 'est. annual DMPK projects' },
  'ADME':                     { total: 2200, desc: 'est. annual ADME studies' },
  'Toxicology':               { total: 1800, desc: 'est. annual tox programs' },
  'Bioanalysis':              { total: 3200, desc: 'est. annual bioanalysis engagements' },
  'CMC':                      { total: 900,  desc: 'est. annual CMC projects' },
  'Clinical Trials':          { total: 4500, desc: 'est. annual clinical engagements' },
  'Regulatory Affairs':       { total: 1100, desc: 'est. regulatory submissions' },
  'Biomarker / Genomics':     { total: 1600, desc: 'est. annual biomarker studies' },
  'Protein Sciences / Biologics': { total: 800, desc: 'est. biologics projects' }
};

function estimateClients(cro) {
  const tierBase = { 1: 0.22, 2: 0.09, 3: 0.03 }[cro.tier] || 0.05;
  const stateBonus = Math.min(0.08, (cro.states || []).length * 0.008);
  const share = tierBase + stateBonus;
  const result = {};
  (cro.services || []).forEach(svc => {
    const mkt = MARKET_SIZE[svc];
    if (!mkt) return;
    const est = Math.round(mkt.total * share);
    result[svc] = { est, share: Math.round(share * 100), desc: mkt.desc };
  });
  return result;
}

// ─── CRO Profile Modal ────────────────────────────────────────────────────────
function openCroModal(croId) {
  const cro = croData.cros.find(c => c.id === croId);
  if (!cro) return;

  const overlay = document.getElementById('cro-modal-overlay');
  document.getElementById('cro-modal-dot').style.background = croColors[cro.id] || '#888';
  document.getElementById('cro-modal-title').textContent = cro.name;
  document.getElementById('cro-modal-sub').textContent = cro.description || '';

  const body = document.getElementById('cro-modal-body');
  const clients = estimateClients(cro);
  const tierLabel = { 1: 'Tier 1 — Global Leader', 2: 'Tier 2 — Regional Specialist', 3: 'Tier 3 — Niche Player' }[cro.tier] || 'CRO';
  const tierClass = 'tier-' + (cro.tier || 2);

  let html = '';

  // Overview
  html += '<div class="modal-section">';
  html += '<div class="modal-section-title">Overview</div>';
  html += '<div class="modal-kv-grid">';
  html += '<div class="modal-kv-key">Tier</div><div class="modal-kv-val"><span class="tier-badge ' + tierClass + '">' + tierLabel + '</span></div>';
  html += '<div class="modal-kv-key">Website</div><div class="modal-kv-val"><a href="https://' + (cro.website || '#') + '" target="_blank">' + (cro.website || '—') + ' ↗</a></div>';
  const stateCount = (cro.states || []).length;
  html += '<div class="modal-kv-key">US Presence</div><div class="modal-kv-val">' + (stateCount > 0 ? stateCount + ' states' : cro.is_medicilon ? 'China-based, expanding to US' : 'Not confirmed') + '</div>';
  if (cro.note) html += '<div class="modal-kv-key">Note</div><div class="modal-kv-val" style="color:var(--gold)">' + cro.note + '</div>';
  html += '</div></div>';

  // US Locations
  if ((cro.states || []).length > 0) {
    html += '<div class="modal-section">';
    html += '<div class="modal-section-title">US States</div>';
    html += '<div class="modal-states-list">';
    cro.states.forEach(function(st) {
      html += '<span class="modal-state-tag" onclick="closeModal();setTimeout(()=>openDetailPanel(\'' + st + '\'),200)">' + st + '</span>';
    });
    html += '</div>';
    if ((cro.cities || []).length > 0) {
      html += '<div style="margin-top:8px;font-size:11px;color:var(--text-muted)">';
      html += cro.cities.map(function(c){ return c.city + ', ' + c.state; }).join(' · ');
      html += '</div>';
    }
    html += '</div>';
  }

  // Services
  html += '<div class="modal-section">';
  html += '<div class="modal-section-title">Services Offered</div>';
  html += '<div class="modal-services-grid">';
  (cro.services || []).forEach(function(svc) {
    const col = SERVICE_COLORS[svc] || '#888';
    html += '<div class="modal-svc-pill"><div class="modal-svc-dot" style="background:' + col + '"></div>' + svc + '</div>';
  });
  html += '</div></div>';

  // Client estimates
  if (!cro.is_medicilon && Object.keys(clients).length > 0) {
    html += '<div class="modal-section">';
    html += '<div class="modal-section-title">Estimated Annual Clients <span style="font-size:9px;color:var(--text-dim);font-weight:400;text-transform:none">(model-based, indicative)</span></div>';
    html += '<div class="client-estimate-grid">';
    const maxEst = Math.max(...Object.values(clients).map(function(v){ return v.est; }), 1);
    Object.entries(clients).forEach(function(entry) {
      const svc = entry[0], data = entry[1];
      const col = SERVICE_COLORS[svc] || '#3b9eff';
      html += '<div class="client-est-card">';
      html += '<div class="client-est-svc">' + svc + '</div>';
      html += '<div class="client-est-num">' + data.est + '</div>';
      html += '<div class="client-est-sub">~' + data.share + '% market share · ' + data.desc + '</div>';
      html += '<div class="client-est-bar-wrap"><div class="client-est-bar" style="width:' + Math.round(data.est/maxEst*100) + '%;background:' + col + '"></div></div>';
      html += '</div>';
    });
    html += '</div></div>';
  }

  // News shortcut
  html += '<div class="modal-section">';
  html += '<button onclick="openNewsForCompany(\'' + cro.short_name + '\');closeModal();" style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:7px 14px;color:var(--accent);font-size:12px;cursor:pointer;font-family:inherit;transition:all 0.15s">📰 View Latest News for ' + cro.short_name + ' →</button>';
  html += '</div>';

  body.innerHTML = html;
  overlay.classList.add('visible');
  document.getElementById('cro-modal-close').onclick = closeModal;
  overlay.onclick = function(e) { if (e.target === overlay) closeModal(); };
}

function closeModal() {
  document.getElementById('cro-modal-overlay').classList.remove('visible');
}

// ─── Marketing / Strategy Panel ───────────────────────────────────────────────
function renderStrategyPanel() {
  const pane = document.getElementById('tab-strategy');
  if (!pane || pane.dataset.rendered) return;
  pane.dataset.rendered = '1';

  const med = croData.cros.find(function(c){ return c.is_medicilon; });
  const medServices = new Set(med ? (med.core_services || med.services) : []);

  // Identify top opportunity states (reuse existing logic)
  const hubWeights = croData.biotech_hub_weights || {};
  const stateScores = Object.keys(hubWeights).map(function(st) {
    const cros = stateIndex[st] || [];
    const coverage = cros.filter(function(c){
      return c.services.some(function(s){ return medServices.has(s); });
    }).length;
    const gap = Math.max(0, 6 - coverage);
    return { st: st, score: (hubWeights[st] || 1) * (gap + 1), coverage: coverage, gap: gap };
  }).sort(function(a,b){ return b.score - a.score; });
  const top5 = stateScores.slice(0, 5);

  // Service whitespace
  const svcCoverage = {};
  croData.cros.forEach(function(cro) {
    if (cro.is_medicilon) return;
    (cro.services || []).forEach(function(s) { svcCoverage[s] = (svcCoverage[s] || 0) + 1; });
  });
  const weakServices = Object.entries(svcCoverage).sort(function(a,b){ return a[1]-b[1]; }).slice(0,3).map(function(e){ return e[0]; });

  const top5Names = top5.map(function(t){ return '<span class="strategy-highlight">' + t.st + '</span>'; }).join('');
  const weakSvcNames = weakServices.map(function(s){ return '<span class="strategy-highlight">' + s + '</span>'; }).join('');

  const cards = [
    {
      icon: '🎯',
      title: 'Priority Entry States',
      body: '<p>Based on biotech client density × CRO service gaps, the top states for Medicilon US expansion are:</p><p style="margin-top:6px">' + top5Names + '</p><ul><li><b>MA & CA</b>: highest biotech density, underserved in In Vivo/DMPK vs demand</li><li><b>NJ</b>: pharma corridor, strong ADME/Tox demand</li><li><b>NC</b>: Research Triangle — fast-growing, less saturated</li><li><b>TX</b>: emerging hub, lower CRO competition</li></ul>'
    },
    {
      icon: '🔬',
      title: 'Service Positioning',
      body: '<p>Medicilon\'s core strengths align with underserved categories:</p>' + weakSvcNames + '<ul style="margin-top:6px"><li><b>In Vivo / Mouse Services</b>: fewer US providers per state than DMPK/Bioanalysis — strong white space</li><li><b>CMC</b>: high demand post-IND, underserved nationally</li><li><b>Protein Sciences</b>: ADC/biologic boom drives demand; few niche providers</li></ul>'
    },
    {
      icon: '⚔️',
      title: 'Competitive Angles',
      body: '<ul><li><b>vs Charles River</b>: price competitiveness + integrated China↔US package (dual-site efficiency)</li><li><b>vs WuXi AppTec</b>: differentiate on turnaround speed and dedicated account management for mid-size biotechs</li><li><b>vs Pharmaron</b>: stronger In Vivo portfolio; target oncology-focused clients</li><li><b>vs regional CROs</b>: offer full preclinical package vs single-service specialists</li></ul>'
    },
    {
      icon: '🤝',
      title: 'Partnership Strategy',
      body: '<ul><li>Target <b>Series A/B biotechs</b> in MA and CA — high IND activity, cost-sensitive, open to Asian CROs</li><li>Partner with <b>US biotech accelerators</b> (MassBio, QB3, JLABS) for introductions</li><li>Consider <b>co-marketing</b> with US-based CROs that lack In Vivo/DMPK (e.g. Syneos, BioAgilytix)</li><li>Engage <b>US investor networks</b> (RA Capital, Flagship) as indirect referral channels</li></ul>'
    },
    {
      icon: '📈',
      title: 'Client Acquisition Forecast',
      body: '<ul><li><b>Year 1</b>: 5–10 US clients via direct outreach + conference presence (BIO, AAPS, SLAS)</li><li><b>Year 2</b>: 20–35 clients with US BD hire + partnership pipeline active</li><li><b>Year 3</b>: 50+ clients with US satellite office or service hub (target NJ or NC)</li></ul><p style="margin-top:6px;font-size:10px;color:var(--text-dim)">Based on comparable Asian CRO US entry trajectories (Pharmaron 2017–2020, WuXi 2014–2018)</p>'
    },
    {
      icon: '⚠️',
      title: 'Risk & Mitigation',
      body: '<ul><li><b>Regulatory perception</b>: FDA scrutiny of China-based CROs — mitigate with US PI/study director hires and GLP certification emphasis</li><li><b>IP concerns</b>: Some US biotechs cautious about China data handling — address proactively in BD materials</li><li><b>Price competition</b>: Tier 1 CROs discounting — compete on speed + package deals, not price alone</li><li><b>Staff capacity</b>: Rapid US growth risk — phase expansion by state</li></ul>',
      fullWidth: true
    }
  ];

  pane.className = 'tab-pane active strategy-grid';
  pane.innerHTML = '';
  cards.forEach(function(card) {
    const div = document.createElement('div');
    div.className = 'strategy-card' + (card.fullWidth ? ' full-width' : '');
    div.innerHTML = '<div class="strategy-card-icon">' + card.icon + '</div><div class="strategy-card-title">' + card.title + '</div><div class="strategy-card-body">' + card.body + '</div>';
    pane.appendChild(div);
  });
}
"""

# Insert before last </script>
last_script = html.rfind('</script>')
html = html[:last_script] + NEW_JS + '\n' + html[last_script:]
print("OK: JS functions added")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. Wire up: company legend items → openCroModal on click
# ═══════════════════════════════════════════════════════════════════════════════
old_legend_item = """    const div = document.createElement('div');
    div.className = 'company-item' + (cro.is_medicilon ? ' medicilon' : '');
    const stateCount = cro.is_medicilon ? '—' : (cro.states?.length || 0);
    div.innerHTML = `
      <div class="company-dot" style="background:${croColors[cro.id]}"></div>
      <div class="company-name">${cro.short_name}</div>
      <div class="company-states">${stateCount} states</div>
    `;
    legend.appendChild(div);"""

new_legend_item = """    const div = document.createElement('div');
    div.className = 'company-item' + (cro.is_medicilon ? ' medicilon' : '');
    div.style.cursor = 'pointer';
    div.title = 'Click for company profile';
    const stateCount = cro.is_medicilon ? '—' : (cro.states?.length || 0);
    const totalEst = cro.is_medicilon ? '' : (() => {
      const cl = estimateClients(cro);
      const total = Object.values(cl).reduce((a,b) => a + b.est, 0);
      return '<div class="company-states" style="color:var(--accent);font-size:9px">~' + total + ' clients</div>';
    })();
    div.innerHTML = `
      <div class="company-dot" style="background:${croColors[cro.id]}"></div>
      <div class="company-name">${cro.short_name}</div>
      <div class="company-states">${stateCount} states</div>
      ${totalEst}
    `;
    div.addEventListener('click', () => openCroModal(cro.id));
    legend.appendChild(div);"""

if old_legend_item in html:
    html = html.replace(old_legend_item, new_legend_item, 1)
    print("OK: Company legend click handler added")
else:
    print("WARNING: Company legend item template not found")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. Wire up strategy tab render on click
# ═══════════════════════════════════════════════════════════════════════════════
old_tab_click = """  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
  });"""

new_tab_click = """  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
      if (btn.dataset.tab === 'strategy') renderStrategyPanel();
    });
  });"""

if old_tab_click in html:
    html = html.replace(old_tab_click, new_tab_click, 1)
    print("OK: Strategy tab render hook added")
else:
    print("WARNING: Tab click handler not found")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. News item hyperlinks — make titles clickable
# ═══════════════════════════════════════════════════════════════════════════════
# In NEWS_DATA, titles don't have URLs, so we'll open a Google News search for the title
old_news_title_line = "      '<div class=\"news-item-title\">' + item.title + '</div>' +"
new_news_title_line = "      '<div class=\"news-item-title\"><a href=\"https://news.google.com/search?q=' + encodeURIComponent(item.title) + '\" target=\"_blank\" style=\"color:inherit;text-decoration:none\" onmouseover=\"this.style.color=\\'var(--accent)\\'\" onmouseout=\"this.style.color=\\'inherit\\'\">' + item.title + ' <span style=\"font-size:9px;opacity:0.6\">↗</span></a></div>' +"

if old_news_title_line in html:
    html = html.replace(old_news_title_line, new_news_title_line, 1)
    print("OK: News title hyperlinks added")
else:
    print("WARNING: News title line not found")

# ═══════════════════════════════════════════════════════════════════════════════
# 7. Write
# ═══════════════════════════════════════════════════════════════════════════════
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done. Final size: {len(html)} bytes")

# Verify
checks = ['openCroModal', 'estimateClients', 'renderStrategyPanel', 'strategy-card',
          'cro-modal-overlay', 'news.google.com', 'tab-strategy', 'client-estimate-grid']
for c in checks:
    print(('OK' if c in html else 'MISSING') + '  ' + c)
