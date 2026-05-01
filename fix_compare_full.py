import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

original_len = len(html)

# ── Replace renderCompareTable + openCompare with full implementation ─────────

OLD_OPEN = "function openCompare() {"
# Find the full block from openCompare through closeCompare
start = html.find("function openCompare() {")
end   = html.find("function closeCompare() {")
end   = html.find("}", end) + 1  # include the closing brace

old_block = html[start:end]

NEW_BLOCK = r"""function openCompare() {
  const overlay = document.getElementById('compare-modal-overlay');
  if (!overlay || !croData) return;

  // Populate both CRO selector dropdowns
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
      if (!current) {
        if (idx === 0) { const m = cros.find(c => c.is_medicilon); if (m) sel.value = m.id; }
        else           { const f = cros.find(c => !c.is_medicilon); if (f) sel.value = f.id; }
      } else { sel.value = current; }
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
  const ids  = Array.from(selects).map(s => s.value).filter(Boolean);
  const cros = ids.map(id => croData.cros.find(c => c.id === id)).filter(Boolean);

  if (cros.length < 2) {
    body.innerHTML = '<div class="compare-placeholder">Select two CROs above to generate a strategic comparison.</div>';
    return;
  }

  const [a, b] = cros;
  const services = croData.service_categories || [];
  const hubWeights = croData.biotech_hub_weights || {};

  // ── Scores ──────────────────────────────────────────────────────────────────
  function croScore(cro) {
    const stateCount = (cro.states || []).length;
    const svcCount   = (cro.services || []).length;
    const hubScore   = (cro.states || []).reduce((s, st) => s + (hubWeights[st] || 0), 0);
    const tierBonus  = cro.tier === 1 ? 30 : cro.tier === 2 ? 20 : 10;
    return Math.min(100, Math.round(stateCount * 3 + svcCount * 4 + hubScore * 0.5 + tierBonus));
  }

  const scoreA = croScore(a), scoreB = croScore(b);

  // ── News for each CRO ───────────────────────────────────────────────────────
  function newsFor(cro) {
    if (!NEWS_DATA || !NEWS_DATA.length) return [];
    return NEWS_DATA.filter(n => (n.tags || []).includes(cro.short_name)).slice(0, 3);
  }
  const newsA = newsFor(a), newsB = newsFor(b);

  // ── Service overlap & gaps ──────────────────────────────────────────────────
  const svcsA = new Set(a.services || []);
  const svcsB = new Set(b.services || []);
  const shared    = services.filter(s => svcsA.has(s) && svcsB.has(s));
  const onlyA     = services.filter(s => svcsA.has(s) && !svcsB.has(s));
  const onlyB     = services.filter(s => !svcsA.has(s) && svcsB.has(s));
  const neitherHas = services.filter(s => !svcsA.has(s) && !svcsB.has(s));

  // ── State overlap ───────────────────────────────────────────────────────────
  const statesA = new Set(a.states || []);
  const statesB = new Set(b.states || []);
  const sharedStates = [...statesA].filter(s => statesB.has(s));
  const onlyAStates  = [...statesA].filter(s => !statesB.has(s));
  const onlyBStates  = [...statesB].filter(s => !statesA.has(s));

  // ── Strategic Suggestions ───────────────────────────────────────────────────
  function generateStrategy(focal, rival, fScore, rScore) {
    const tips = [];
    const fName = focal.short_name, rName = rival.short_name;
    const fMed = focal.is_medicilon, rMed = rival.is_medicilon;
    const fLabel = fMed ? 'Medicilon' : fName;

    // Service gaps
    const fMissing = services.filter(s => !(focal.services||[]).includes(s) && (rival.services||[]).includes(s));
    if (fMissing.length) {
      tips.push({
        icon: '🎯', type: 'Gap',
        text: `<b>${fLabel}</b> lacks <b>${fMissing.slice(0,3).join(', ')}</b> — capabilities ${rName} uses as differentiators. Consider partnerships or capability build-out.`
      });
    }

    // Geographic gaps
    const fMissingStates = [...statesB].filter(s => !statesA.has(s));
    const topMissing = fMissingStates.filter(s => (hubWeights[s]||0) >= 7).slice(0,3);
    if (topMissing.length) {
      tips.push({
        icon: '📍', type: 'Geography',
        text: `${rName} has presence in high-value states <b>${topMissing.join(', ')}</b> where ${fLabel} is absent. These are priority entry markets.`
      });
    }

    // Unique strengths of focal
    const fUnique = services.filter(s => (focal.services||[]).includes(s) && !(rival.services||[]).includes(s));
    if (fUnique.length) {
      tips.push({
        icon: '💪', type: 'Strength',
        text: `${fLabel} exclusively offers <b>${fUnique.slice(0,3).join(', ')}</b> vs ${rName} — lean into these as competitive differentiators in marketing.`
      });
    }

    // Score delta
    if (fScore < rScore - 10) {
      tips.push({
        icon: '⚡', type: 'Priority',
        text: `${rName} has a significant market footprint advantage (score ${rScore} vs ${fScore}). Prioritise state presence and service breadth to close the gap.`
      });
    } else if (fScore > rScore + 10) {
      tips.push({
        icon: '🏆', type: 'Advantage',
        text: `${fLabel} leads in overall footprint (score ${fScore} vs ${rScore}). Defend position in shared states; use scale advantage for pricing.`
      });
    }

    // Shared state competition
    if (sharedStates.length > 3) {
      tips.push({
        icon: '⚔️', type: 'Competition',
        text: `Both compete directly in <b>${sharedStates.length} states</b> (${sharedStates.slice(0,4).join(', ')}…). Differentiate on turnaround time, price, or niche specialisation.`
      });
    }

    // Whitespace opportunity
    if (neitherHas.length) {
      tips.push({
        icon: '🌐', type: 'Whitespace',
        text: `Neither ${fLabel} nor ${rName} covers <b>${neitherHas.slice(0,2).join(', ')}</b> — market whitespace opportunity with no direct competition from either.`
      });
    }

    return tips.slice(0, 5);
  }

  const stratA = generateStrategy(a, b, scoreA, scoreB);
  const stratB = generateStrategy(b, a, scoreB, scoreA);

  // ── Render HTML ─────────────────────────────────────────────────────────────
  function scoreBar(score, color) {
    return `<div class="cmp-score-bar-wrap"><div class="cmp-score-bar" style="width:${score}%;background:${color}"></div></div>`;
  }

  function newsHtml(articles) {
    if (!articles.length) return '<div class="cmp-no-news">No recent news found</div>';
    return articles.map(n =>
      `<div class="cmp-news-item">
        <div class="cmp-news-title">${n.title.length > 80 ? n.title.slice(0,80)+'…' : n.title}</div>
        <div class="cmp-news-meta">${n.source} · ${n.date}</div>
      </div>`
    ).join('');
  }

  function tagList(arr, cls) {
    if (!arr.length) return '<span class="cmp-none">—</span>';
    return arr.map(s => `<span class="cmp-tag ${cls}">${s}</span>`).join('');
  }

  function stratHtml(tips) {
    if (!tips.length) return '<div class="cmp-no-news">No suggestions generated</div>';
    return tips.map(t =>
      `<div class="cmp-strat-item">
        <span class="cmp-strat-icon">${t.icon}</span>
        <div><span class="cmp-strat-type">${t.type}</span> ${t.text}</div>
      </div>`
    ).join('');
  }

  const colA = a.is_medicilon ? 'var(--gold)' : 'var(--accent)';
  const colB = b.is_medicilon ? 'var(--gold)' : '#9b59b6';

  body.innerHTML = `
    <!-- Score header -->
    <div class="cmp-score-row">
      <div class="cmp-score-card" style="border-color:${colA}">
        <div class="cmp-score-name" style="color:${colA}">${a.is_medicilon?'⭐ ':''}${a.short_name}</div>
        <div class="cmp-score-val">${scoreA}<span>/100</span></div>
        ${scoreBar(scoreA, colA)}
        <div class="cmp-score-meta">Tier ${a.tier||'?'} · ${(a.states||[]).length} states · ${(a.services||[]).length} services</div>
      </div>
      <div class="cmp-vs">VS</div>
      <div class="cmp-score-card" style="border-color:${colB}">
        <div class="cmp-score-name" style="color:${colB}">${b.is_medicilon?'⭐ ':''}${b.short_name}</div>
        <div class="cmp-score-val">${scoreB}<span>/100</span></div>
        ${scoreBar(scoreB, colB)}
        <div class="cmp-score-meta">Tier ${b.tier||'?'} · ${(b.states||[]).length} states · ${(b.services||[]).length} services</div>
      </div>
    </div>

    <!-- Service comparison -->
    <div class="cmp-section">
      <div class="cmp-section-title">Service Coverage</div>
      <div class="cmp-service-grid">
        <div class="cmp-service-col">
          <div class="cmp-col-hdr" style="color:${colA}">Only ${a.short_name}</div>
          ${tagList(onlyA, 'tag-a')}
        </div>
        <div class="cmp-service-col">
          <div class="cmp-col-hdr" style="color:var(--text-muted)">Both Cover</div>
          ${tagList(shared, 'tag-shared')}
        </div>
        <div class="cmp-service-col">
          <div class="cmp-col-hdr" style="color:${colB}">Only ${b.short_name}</div>
          ${tagList(onlyB, 'tag-b')}
        </div>
      </div>
    </div>

    <!-- Geographic overlap -->
    <div class="cmp-section">
      <div class="cmp-section-title">Geographic Footprint</div>
      <div class="cmp-service-grid">
        <div class="cmp-service-col">
          <div class="cmp-col-hdr" style="color:${colA}">Only ${a.short_name}</div>
          ${tagList(onlyAStates, 'tag-a')}
        </div>
        <div class="cmp-service-col">
          <div class="cmp-col-hdr" style="color:var(--text-muted)">Both Present</div>
          ${tagList(sharedStates, 'tag-shared')}
        </div>
        <div class="cmp-service-col">
          <div class="cmp-col-hdr" style="color:${colB}">Only ${b.short_name}</div>
          ${tagList(onlyBStates, 'tag-b')}
        </div>
      </div>
    </div>

    <!-- Recent News -->
    <div class="cmp-section">
      <div class="cmp-section-title">Recent Intelligence</div>
      <div class="cmp-two-col">
        <div class="cmp-news-col">
          <div class="cmp-col-hdr" style="color:${colA}">${a.short_name}</div>
          ${newsHtml(newsA)}
        </div>
        <div class="cmp-news-col">
          <div class="cmp-col-hdr" style="color:${colB}">${b.short_name}</div>
          ${newsHtml(newsB)}
        </div>
      </div>
    </div>

    <!-- Strategic Suggestions -->
    <div class="cmp-section">
      <div class="cmp-section-title">Strategic Suggestions for ${a.short_name}</div>
      <div class="cmp-strat-list">${stratHtml(stratA)}</div>
    </div>
    <div class="cmp-section">
      <div class="cmp-section-title">Strategic Suggestions for ${b.short_name}</div>
      <div class="cmp-strat-list">${stratHtml(stratB)}</div>
    </div>
  `;
}

function closeCompare() {
  const overlay = document.getElementById('compare-modal-overlay');
  if (overlay) overlay.classList.remove('visible');
}"""

html = html[:start] + NEW_BLOCK + html[end:]
print("Replaced openCompare/renderCompareTable/closeCompare block")

# ── Add CSS for compare panel ─────────────────────────────────────────────────
COMPARE_CSS = """
/* ── Compare Panel Internals ─────────────────────────────────── */
.compare-placeholder { padding: 40px; text-align: center; color: var(--text-dim); font-size: 13px; }
.cmp-score-row { display: flex; align-items: center; gap: 12px; padding: 16px 20px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.cmp-score-card { flex: 1; background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; border-top-width: 3px !important; }
.cmp-score-name { font-size: 13px; font-weight: 700; margin-bottom: 6px; }
.cmp-score-val { font-size: 28px; font-weight: 800; font-family: var(--font-display); line-height: 1; }
.cmp-score-val span { font-size: 13px; color: var(--text-dim); font-weight: 400; }
.cmp-score-bar-wrap { background: var(--surface3); border-radius: 4px; height: 5px; margin: 8px 0; overflow: hidden; }
.cmp-score-bar { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
.cmp-score-meta { font-size: 10px; color: var(--text-dim); }
.cmp-vs { font-size: 18px; font-weight: 800; color: var(--text-dim); flex-shrink: 0; }
.cmp-section { padding: 14px 20px; border-bottom: 1px solid var(--border); }
.cmp-section:last-child { border-bottom: none; }
.cmp-section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim); margin-bottom: 10px; font-family: var(--font-display); }
.cmp-service-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
.cmp-service-col { display: flex; flex-direction: column; gap: 4px; }
.cmp-col-hdr { font-size: 10px; font-weight: 600; margin-bottom: 4px; }
.cmp-tag { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 4px; margin: 2px 2px 0 0; }
.tag-a { background: rgba(59,158,255,0.12); border: 1px solid rgba(59,158,255,0.3); color: var(--accent); }
.tag-b { background: rgba(155,89,182,0.12); border: 1px solid rgba(155,89,182,0.3); color: #9b59b6; }
.tag-shared { background: rgba(46,204,113,0.1); border: 1px solid rgba(46,204,113,0.3); color: #2ecc71; }
.cmp-none { font-size: 11px; color: var(--text-dim); }
.cmp-two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.cmp-news-col { display: flex; flex-direction: column; gap: 6px; }
.cmp-news-item { background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; }
.cmp-news-title { font-size: 11px; font-weight: 500; line-height: 1.4; margin-bottom: 3px; }
.cmp-news-meta { font-size: 10px; color: var(--text-dim); }
.cmp-no-news { font-size: 11px; color: var(--text-dim); padding: 8px 0; }
.cmp-strat-list { display: flex; flex-direction: column; gap: 8px; }
.cmp-strat-item { display: flex; gap: 10px; align-items: flex-start; background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 10px 12px; font-size: 12px; line-height: 1.5; }
.cmp-strat-icon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }
.cmp-strat-type { display: inline-block; font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--accent); margin-right: 6px; letter-spacing: 0.05em; }
#compare-modal-body { overflow-y: auto; flex: 1; }
"""

if '.cmp-score-row' not in html:
    html = html.replace('</style>', COMPARE_CSS + '\n</style>', 1)
    print("Added compare panel CSS")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done: {original_len:,} -> {len(html):,} bytes")
