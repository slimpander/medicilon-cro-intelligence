import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

original_len = len(html)
changes = []

# ── 1. Add Compare tab button ─────────────────────────────────────────────────
OLD_TABS = '<button class="tab-btn" data-tab="timeline">🕐 Timeline</button>'
NEW_TABS = (
    '<button class="tab-btn" data-tab="timeline">🕐 Timeline</button>\n'
    '        <button class="tab-btn" data-tab="compare">⚖️ Compare</button>'
)
if OLD_TABS in html:
    html = html.replace(OLD_TABS, NEW_TABS, 1)
    changes.append("Added Compare tab button")

# ── 2. Add Compare tab pane HTML (with selectors + content div) ───────────────
OLD_TIMELINE_PANE = '<div class="tab-pane" id="tab-timeline"></div></div>'
NEW_TIMELINE_PANE = (
    '<div class="tab-pane" id="tab-timeline"></div>\n'
    '        <div class="tab-pane" id="tab-compare">\n'
    '          <div id="compare-tab-header">\n'
    '            <div class="compare-tab-selector">\n'
    '              <label>Company A</label>\n'
    '              <select class="compare-tab-select" id="compare-tab-a"></select>\n'
    '            </div>\n'
    '            <div class="cmp-vs-inline">VS</div>\n'
    '            <div class="compare-tab-selector">\n'
    '              <label>Company B</label>\n'
    '              <select class="compare-tab-select" id="compare-tab-b"></select>\n'
    '            </div>\n'
    '          </div>\n'
    '          <div id="compare-tab-body"></div>\n'
    '        </div>\n'
    '      </div>'
)
if OLD_TIMELINE_PANE in html:
    html = html.replace(OLD_TIMELINE_PANE, NEW_TIMELINE_PANE, 1)
    changes.append("Added Compare tab pane HTML with selectors")

# ── 3. Add Compare tab CSS ────────────────────────────────────────────────────
COMPARE_TAB_CSS = """
/* ── Compare Tab (inline panel) ─────────────────────────────── */
#tab-compare { display: none; flex-direction: column; padding: 0 !important; overflow: hidden; }
#tab-compare.active { display: flex !important; }
#compare-tab-header {
  display: flex; align-items: center; gap: 16px; padding: 10px 16px;
  border-bottom: 1px solid var(--border); flex-shrink: 0;
  background: var(--surface2);
}
.compare-tab-selector { display: flex; align-items: center; gap: 8px; }
.compare-tab-selector label { font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--text-dim); white-space: nowrap; }
.compare-tab-select {
  background: var(--surface3); border: 1px solid var(--border); border-radius: 6px;
  padding: 5px 10px; color: var(--text); font-size: 12px; font-family: var(--font-body);
  outline: none; cursor: pointer; min-width: 160px;
}
.compare-tab-select:focus { border-color: var(--accent); }
.cmp-vs-inline { font-size: 13px; font-weight: 800; color: var(--text-dim); flex-shrink: 0; }
#compare-tab-body {
  flex: 1; overflow-y: auto; overflow-x: hidden;
  display: grid; grid-template-columns: 1fr 1fr; gap: 0;
}
#compare-tab-body::-webkit-scrollbar { width: 4px; }
#compare-tab-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

/* Score strip */
.cmp-tab-scores { grid-column: 1/-1; display: flex; gap: 0; border-bottom: 1px solid var(--border); }
.cmp-tab-score-card { flex: 1; padding: 10px 16px; display: flex; align-items: center; gap: 12px; }
.cmp-tab-score-card:first-child { border-right: 1px solid var(--border); }
.cmp-tab-score-name { font-size: 12px; font-weight: 700; flex: 1; }
.cmp-tab-score-num { font-size: 22px; font-weight: 800; font-family: var(--font-display); }
.cmp-tab-score-sub { font-size: 10px; color: var(--text-dim); }

/* Column layout */
.cmp-tab-col { padding: 12px 16px; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; }
.cmp-tab-col:first-of-type { border-right: 1px solid var(--border); }
.cmp-tab-section { display: flex; flex-direction: column; gap: 5px; }
.cmp-tab-section-title { font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--text-dim); padding-bottom: 4px;
  border-bottom: 1px solid var(--border); margin-bottom: 2px; }
.cmp-tab-tags { display: flex; flex-wrap: wrap; gap: 3px; }
.cmp-tab-tag { font-size: 10px; padding: 2px 6px; border-radius: 3px; }
.cmp-tab-tag.has  { background: rgba(46,204,113,0.12); border: 1px solid rgba(46,204,113,0.3); color: #2ecc71; }
.cmp-tab-tag.miss { background: rgba(231,76,60,0.1);   border: 1px solid rgba(231,76,60,0.25); color: #e74c3c; }
.cmp-tab-tag.state{ background: rgba(59,158,255,0.1);  border: 1px solid rgba(59,158,255,0.25); color: var(--accent); }
.cmp-tab-news { display: flex; flex-direction: column; gap: 5px; }
.cmp-tab-news-item { background: var(--surface2); border: 1px solid var(--border);
  border-radius: 5px; padding: 7px 9px; }
.cmp-tab-news-title { font-size: 11px; font-weight: 500; line-height: 1.35; margin-bottom: 2px; }
.cmp-tab-news-meta  { font-size: 10px; color: var(--text-dim); }
.cmp-tab-strat { display: flex; flex-direction: column; gap: 5px; }
.cmp-tab-strat-item { display: flex; gap: 8px; align-items: flex-start;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 5px; padding: 7px 9px; font-size: 11px; line-height: 1.45; }
.cmp-tab-strat-icon { font-size: 13px; flex-shrink: 0; }
.cmp-tab-strat-type { font-size: 9px; font-weight: 700; text-transform: uppercase;
  color: var(--accent); margin-right: 5px; letter-spacing: 0.05em; }
.cmp-tab-score-bar-wrap { flex: 1; background: var(--surface3); border-radius: 3px; height: 4px; overflow: hidden; }
.cmp-tab-score-bar { height: 100%; border-radius: 3px; }
.cmp-tab-placeholder { grid-column: 1/-1; display: flex; align-items: center;
  justify-content: center; color: var(--text-dim); font-size: 13px; padding: 40px; }
"""

if '#tab-compare' not in html or 'cmp-tab-scores' not in html:
    html = html.replace('</style>', COMPARE_TAB_CSS + '\n</style>', 1)
    changes.append("Added Compare tab CSS")

# ── 4. Add renderCompareTab() JS function and wire it up ─────────────────────
COMPARE_TAB_JS = r"""
// ─── Compare Tab ──────────────────────────────────────────────────────────────
function initCompareTab() {
  const selA = document.getElementById('compare-tab-a');
  const selB = document.getElementById('compare-tab-b');
  if (!selA || !selB || !croData) return;

  const cros = croData.cros || [];

  [selA, selB].forEach((sel, idx) => {
    sel.innerHTML = '<option value="">— Select —</option>';
    cros.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = (c.is_medicilon ? '⭐ ' : '') + c.short_name;
      sel.appendChild(opt);
    });
    // Defaults: A = Medicilon, B = first competitor
    const def = idx === 0 ? cros.find(c => c.is_medicilon) : cros.find(c => !c.is_medicilon);
    if (def) sel.value = def.id;
    sel.addEventListener('change', renderCompareTab);
  });

  renderCompareTab();
}

function renderCompareTab() {
  const body = document.getElementById('compare-tab-body');
  if (!body || !croData) return;

  const selA = document.getElementById('compare-tab-a');
  const selB = document.getElementById('compare-tab-b');
  const idA  = selA ? selA.value : '';
  const idB  = selB ? selB.value : '';

  if (!idA || !idB) {
    body.innerHTML = '<div class="cmp-tab-placeholder">Select two companies above to compare.</div>';
    return;
  }

  const a = croData.cros.find(c => c.id === idA);
  const b = croData.cros.find(c => c.id === idB);
  if (!a || !b) return;

  const services    = croData.service_categories || [];
  const hubWeights  = croData.biotech_hub_weights || {};

  // Score
  function croScore(cro) {
    const stateCount = (cro.states || []).length;
    const svcCount   = (cro.services || []).length;
    const hubScore   = (cro.states || []).reduce((s, st) => s + (hubWeights[st] || 0), 0);
    const tierBonus  = cro.tier === 1 ? 30 : cro.tier === 2 ? 20 : 10;
    return Math.min(100, Math.round(stateCount * 3 + svcCount * 4 + hubScore * 0.5 + tierBonus));
  }
  const scoreA = croScore(a), scoreB = croScore(b);

  // Services
  const svcsA = new Set(a.services || []);
  const svcsB = new Set(b.services || []);

  // States
  const statesA = new Set(a.states || []);
  const statesB = new Set(b.states || []);
  const sharedStates = [...statesA].filter(s => statesB.has(s));

  // News
  function newsFor(cro) {
    if (!NEWS_DATA || !NEWS_DATA.length) return [];
    return NEWS_DATA.filter(n => (n.tags || []).includes(cro.short_name)).slice(0, 4);
  }

  // Strategy suggestions for focal vs rival
  function genStrategy(focal, rival) {
    const tips = [];
    const fName  = focal.short_name;
    const rName  = rival.short_name;
    const fSvcs  = new Set(focal.services || []);
    const rSvcs  = new Set(rival.services || []);
    const fStates = new Set(focal.states || []);
    const rStates = new Set(rival.states || []);

    const fMissing = services.filter(s => !fSvcs.has(s) && rSvcs.has(s));
    if (fMissing.length)
      tips.push({ icon:'🎯', type:'Gap',
        text:`<b>${fName}</b> lacks <b>${fMissing.slice(0,3).join(', ')}</b> that ${rName} offers — consider build-out or partnerships.` });

    const topMissingStates = [...rStates].filter(s => !fStates.has(s) && (hubWeights[s]||0) >= 7).slice(0,4);
    if (topMissingStates.length)
      tips.push({ icon:'📍', type:'Geography',
        text:`${rName} is in high-value states <b>${topMissingStates.join(', ')}</b> where <b>${fName}</b> is absent — priority entry markets.` });

    const fUnique = services.filter(s => fSvcs.has(s) && !rSvcs.has(s));
    if (fUnique.length)
      tips.push({ icon:'💪', type:'Strength',
        text:`<b>${fName}</b> exclusively offers <b>${fUnique.slice(0,3).join(', ')}</b> — differentiate and market these against ${rName}.` });

    const fScore = croScore(focal), rScore = croScore(rival);
    if (fScore < rScore - 10)
      tips.push({ icon:'⚡', type:'Priority',
        text:`${rName} leads overall footprint (${rScore} vs ${fScore}). Expand state presence and service depth to close the gap.` });
    else if (fScore > rScore + 10)
      tips.push({ icon:'🏆', type:'Advantage',
        text:`<b>${fName}</b> leads (${fScore} vs ${rScore}). Leverage scale for pricing power and defend shared states.` });

    if (sharedStates.length > 2)
      tips.push({ icon:'⚔️', type:'Competition',
        text:`Both compete in <b>${sharedStates.length} shared states</b> (${sharedStates.slice(0,4).join(', ')}…). Differentiate on turnaround time, niche or price.` });

    return tips.slice(0, 4);
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  const colA = a.is_medicilon ? 'var(--gold)' : 'var(--accent)';
  const colB = b.is_medicilon ? 'var(--gold)' : '#9b59b6';

  function tagRow(svcs, has, color) {
    if (!svcs.length) return '<span style="font-size:10px;color:var(--text-dim)">—</span>';
    return svcs.map(s =>
      `<span class="cmp-tab-tag ${has ? 'has' : 'miss'}">${s}</span>`
    ).join('');
  }

  function stateTagRow(states) {
    if (!states.length) return '<span style="font-size:10px;color:var(--text-dim)">None</span>';
    return states.map(s => `<span class="cmp-tab-tag state">${s}</span>`).join('');
  }

  function newsCol(articles) {
    if (!articles.length) return '<div style="font-size:11px;color:var(--text-dim)">No recent news found</div>';
    return '<div class="cmp-tab-news">' + articles.map(n =>
      `<div class="cmp-tab-news-item">
        <div class="cmp-tab-news-title">${n.title.length > 90 ? n.title.slice(0,90)+'…' : n.title}</div>
        <div class="cmp-tab-news-meta">${n.source} · ${n.date}</div>
      </div>`
    ).join('') + '</div>';
  }

  function stratCol(tips) {
    if (!tips.length) return '<div style="font-size:11px;color:var(--text-dim)">No suggestions</div>';
    return '<div class="cmp-tab-strat">' + tips.map(t =>
      `<div class="cmp-tab-strat-item">
        <span class="cmp-tab-strat-icon">${t.icon}</span>
        <div><span class="cmp-tab-strat-type">${t.type}</span>${t.text}</div>
      </div>`
    ).join('') + '</div>';
  }

  const newsA = newsFor(a), newsB = newsFor(b);
  const stratA = genStrategy(a, b), stratB = genStrategy(b, a);

  const onlyA  = services.filter(s => svcsA.has(s) && !svcsB.has(s));
  const onlyB  = services.filter(s => !svcsA.has(s) && svcsB.has(s));
  const shared = services.filter(s => svcsA.has(s) && svcsB.has(s));
  const onlyAStates = [...statesA].filter(s => !statesB.has(s));
  const onlyBStates = [...statesB].filter(s => !statesA.has(s));

  body.innerHTML = `
    <!-- Score strip -->
    <div class="cmp-tab-scores">
      <div class="cmp-tab-score-card">
        <div>
          <div class="cmp-tab-score-name" style="color:${colA}">${a.is_medicilon?'⭐ ':''}${a.short_name}</div>
          <div class="cmp-tab-score-sub">Tier ${a.tier||'?'} · ${(a.states||[]).length} states · ${(a.services||[]).length} services</div>
        </div>
        <div>
          <div class="cmp-tab-score-num" style="color:${colA}">${scoreA}<span style="font-size:11px;color:var(--text-dim)">/100</span></div>
          <div class="cmp-tab-score-bar-wrap"><div class="cmp-tab-score-bar" style="width:${scoreA}%;background:${colA}"></div></div>
        </div>
      </div>
      <div class="cmp-tab-score-card">
        <div>
          <div class="cmp-tab-score-name" style="color:${colB}">${b.is_medicilon?'⭐ ':''}${b.short_name}</div>
          <div class="cmp-tab-score-sub">Tier ${b.tier||'?'} · ${(b.states||[]).length} states · ${(b.services||[]).length} services</div>
        </div>
        <div>
          <div class="cmp-tab-score-num" style="color:${colB}">${scoreB}<span style="font-size:11px;color:var(--text-dim)">/100</span></div>
          <div class="cmp-tab-score-bar-wrap"><div class="cmp-tab-score-bar" style="width:${scoreB}%;background:${colB}"></div></div>
        </div>
      </div>
    </div>

    <!-- Two columns -->
    <div class="cmp-tab-col">
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title" style="color:${colA}">Services — ${a.short_name}</div>
        <div class="cmp-tab-tags">${tagRow(Array.from(svcsA), true, colA)}</div>
      </div>
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title">Exclusive to ${a.short_name}</div>
        <div class="cmp-tab-tags">${tagRow(onlyA, true, colA)}</div>
      </div>
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title">Missing vs ${b.short_name}</div>
        <div class="cmp-tab-tags">${tagRow(onlyB, false, colA)}</div>
      </div>
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title">States — ${a.short_name}</div>
        <div class="cmp-tab-tags">${stateTagRow([...statesA])}</div>
      </div>
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title">Recent News</div>
        ${newsCol(newsA)}
      </div>
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title">Strategy Suggestions</div>
        ${stratCol(stratA)}
      </div>
    </div>

    <div class="cmp-tab-col">
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title" style="color:${colB}">Services — ${b.short_name}</div>
        <div class="cmp-tab-tags">${tagRow(Array.from(svcsB), true, colB)}</div>
      </div>
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title">Exclusive to ${b.short_name}</div>
        <div class="cmp-tab-tags">${tagRow(onlyB, true, colB)}</div>
      </div>
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title">Missing vs ${a.short_name}</div>
        <div class="cmp-tab-tags">${tagRow(onlyA, false, colB)}</div>
      </div>
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title">States — ${b.short_name}</div>
        <div class="cmp-tab-tags">${stateTagRow([...statesB])}</div>
      </div>
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title">Recent News</div>
        ${newsCol(newsB)}
      </div>
      <div class="cmp-tab-section">
        <div class="cmp-tab-section-title">Strategy Suggestions</div>
        ${stratCol(stratB)}
      </div>
    </div>

    <!-- Shared row -->
    <div style="grid-column:1/-1;padding:10px 16px;border-top:1px solid var(--border);background:var(--surface2)">
      <div class="cmp-tab-section-title">Both Cover (${shared.length} services · ${sharedStates.length} shared states)</div>
      <div class="cmp-tab-tags" style="margin-top:4px">
        ${shared.map(s=>`<span class="cmp-tab-tag has">${s}</span>`).join('')}
        ${sharedStates.map(s=>`<span class="cmp-tab-tag state">${s}</span>`).join('')}
      </div>
    </div>
  `;
}
"""

# Insert before init()
INSERT_BEFORE = 'async function init(){'
if 'function initCompareTab' not in html:
    html = html.replace(INSERT_BEFORE, COMPARE_TAB_JS + '\n' + INSERT_BEFORE, 1)
    changes.append("Added initCompareTab() and renderCompareTab() functions")

# ── 5. Call initCompareTab() in renderBottomPanels ───────────────────────────
OLD_BOTTOM = 'function renderBottomPanels(){renderOpportunities();renderWhitespace();renderUnderserved();}'
NEW_BOTTOM = 'function renderBottomPanels(){renderOpportunities();renderWhitespace();renderUnderserved();initCompareTab();}'
if OLD_BOTTOM in html:
    html = html.replace(OLD_BOTTOM, NEW_BOTTOM, 1)
    changes.append("Wired initCompareTab() into renderBottomPanels()")

# ── Write ─────────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"index.html: {original_len:,} -> {len(html):,} bytes\n")
for c in changes:
    print(f"  OK {c}")
