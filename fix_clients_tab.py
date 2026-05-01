import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

original_len = len(html)
changes = []

# ── 1. Remove Compare tab button from bottom panel ────────────────────────────
OLD_COMPARE_BTN = "\n        <button class=\"tab-btn\" data-tab=\"compare\">⚖️ Compare</button>"
if OLD_COMPARE_BTN in html:
    html = html.replace(OLD_COMPARE_BTN, '', 1)
    changes.append("Removed Compare tab button from bottom panel")

# ── 2. Remove Compare tab pane from bottom panel ──────────────────────────────
# Find and remove the entire #tab-compare div
compare_pane_start = html.find('        <div class="tab-pane" id="tab-compare">')
if compare_pane_start < 0:
    compare_pane_start = html.find('<div class="tab-pane" id="tab-compare">')

if compare_pane_start >= 0:
    # Find its closing </div>
    depth = 0; i = compare_pane_start; started = False
    while i < len(html):
        if html[i:i+4] == '<div': depth += 1; started = True
        elif html[i:i+6] == '</div>':
            depth -= 1
            if started and depth == 0:
                end = i + 6
                break
        i += 1
    html = html[:compare_pane_start] + html[end:]
    changes.append("Removed #tab-compare pane from bottom panel")

# ── 3. Add Potential Clients tab button ───────────────────────────────────────
OLD_TIMELINE_BTN = '<button class="tab-btn" data-tab="timeline">🕐 Timeline</button>'
NEW_TIMELINE_BTN = (
    '<button class="tab-btn" data-tab="timeline">🕐 Timeline</button>\n'
    '        <button class="tab-btn" data-tab="clients">🚀 Potential Clients</button>'
)
if OLD_TIMELINE_BTN in html:
    html = html.replace(OLD_TIMELINE_BTN, NEW_TIMELINE_BTN, 1)
    changes.append("Added Potential Clients tab button")

# ── 4. Add Potential Clients tab pane ─────────────────────────────────────────
OLD_TIMELINE_PANE = '<div class="tab-pane" id="tab-timeline"></div>\n      </div>'
NEW_TIMELINE_PANE = (
    '<div class="tab-pane" id="tab-timeline"></div>\n'
    '        <div class="tab-pane" id="tab-clients"></div>\n'
    '      </div>'
)
if OLD_TIMELINE_PANE in html:
    html = html.replace(OLD_TIMELINE_PANE, NEW_TIMELINE_PANE, 1)
    changes.append("Added #tab-clients pane")
else:
    # fallback
    OLD2 = '<div class="tab-pane" id="tab-timeline"></div>'
    if OLD2 in html:
        html = html.replace(OLD2, OLD2 + '\n        <div class="tab-pane" id="tab-clients"></div>', 1)
        changes.append("Added #tab-clients pane (fallback)")

# ── 5. Add CSS for clients tab ────────────────────────────────────────────────
CLIENTS_CSS = """
/* ── Potential Clients Tab ───────────────────────────────── */
.client-card {
  background: var(--surface2); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px 14px; min-width: 200px; max-width: 240px; flex-shrink: 0;
  display: flex; flex-direction: column; gap: 6px; cursor: pointer;
  transition: border-color 0.15s, transform 0.1s;
}
.client-card:hover { border-color: var(--accent); transform: translateY(-1px); }
.client-card-header { display: flex; align-items: center; gap: 8px; }
.client-stage-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.client-name { font-size: 12px; font-weight: 700; flex: 1; line-height: 1.3; }
.client-state-badge {
  font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 3px;
  background: rgba(59,158,255,0.12); border: 1px solid rgba(59,158,255,0.3);
  color: var(--accent); flex-shrink: 0;
}
.client-focus { font-size: 10px; color: var(--text-muted); line-height: 1.4; }
.client-tags { display: flex; flex-wrap: wrap; gap: 3px; }
.client-tag {
  font-size: 9px; padding: 1px 5px; border-radius: 3px;
  background: var(--surface3); border: 1px solid var(--border); color: var(--text-dim);
}
.client-tag.need { background: rgba(46,204,113,0.1); border-color: rgba(46,204,113,0.3); color: #2ecc71; }
.client-opportunity { font-size: 10px; color: var(--gold); font-weight: 600; }
.client-stage-label { font-size: 9px; color: var(--text-dim); }
#clients-toolbar {
  display: flex; gap: 8px; align-items: center; padding: 8px 16px;
  border-bottom: 1px solid var(--border); flex-shrink: 0; flex-wrap: wrap;
}
#clients-toolbar select, #clients-toolbar input {
  background: var(--surface2); border: 1px solid var(--border); border-radius: 5px;
  padding: 4px 8px; color: var(--text); font-size: 11px; font-family: var(--font-body); outline: none;
}
#clients-toolbar label { font-size: 10px; color: var(--text-dim); font-weight: 600; }
#clients-count { font-size: 10px; color: var(--text-dim); margin-left: auto; }
#tab-clients { flex-direction: column !important; padding: 0 !important; }
#tab-clients.active { display: flex !important; }
#clients-body {
  flex: 1; overflow-x: auto; overflow-y: hidden;
  display: flex; gap: 10px; align-items: flex-start;
  padding: 12px 16px; flex-wrap: nowrap;
}
#clients-body::-webkit-scrollbar { height: 4px; }
#clients-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
"""

if '.client-card' not in html:
    html = html.replace('</style>', CLIENTS_CSS + '\n</style>', 1)
    changes.append("Added Potential Clients CSS")

# ── 6. Add renderClients() JS ─────────────────────────────────────────────────
CLIENTS_JS = r"""
// ─── Potential Clients Tab ────────────────────────────────────────────────────
// Curated list of emerging biotechs by state — likely CRO service buyers
const POTENTIAL_CLIENTS = [
  // Massachusetts (hub weight 10)
  { name:'Relay Therapeutics', state:'MA', stage:'Phase II', focus:'Precision oncology, protein motion', needs:['DMPK','Bioanalysis','In Vivo / Mouse Services'], founded:2016, opportunity:'High — active IND pipeline, multiple CRO partnerships' },
  { name:'Kymera Therapeutics', state:'MA', stage:'Phase II', focus:'Targeted protein degradation', needs:['DMPK','ADME','Toxicology'], founded:2016, opportunity:'High — degrader DMPK is specialty gap' },
  { name:'Larimar Therapeutics', state:'MA', stage:'Phase II', focus:'Rare diseases, mitochondrial', needs:['Toxicology','Bioanalysis','Regulatory Affairs'], founded:2015, opportunity:'Medium — rare disease tox packages' },
  { name:'Disc Medicine', state:'MA', stage:'Phase II', focus:'Hematologic diseases', needs:['Bioanalysis','DMPK'], founded:2021, opportunity:'Medium — early-stage bioanalysis' },
  { name:'Flagship Pioneering portfolio', state:'MA', stage:'Seed/Series A', focus:'Platform biotech', needs:['In Vivo / Mouse Services','CMC','DMPK'], founded:2022, opportunity:'High — multiple early programs, cost-sensitive' },

  // California (hub weight 10)
  { name:'Absci Corporation', state:'CA', stage:'Platform', focus:'Generative AI drug design', needs:['Protein Sciences / Biologics','Bioanalysis'], founded:2011, opportunity:'High — biologics characterisation gap' },
  { name:'Septerna', state:'CA', stage:'Series B', focus:'GPCR-targeted small molecules', needs:['DMPK','ADME','In Vivo / Mouse Services'], founded:2022, opportunity:'High — DMPK for GPCR program' },
  { name:'Protagonist Therapeutics', state:'CA', stage:'Phase III', focus:'Peptide therapeutics, hematology', needs:['DMPK','Bioanalysis','CMC'], founded:2008, opportunity:'Medium — peptide DMPK specialist' },
  { name:'Turning Point Therapeutics', state:'CA', stage:'Acquired/spinout', focus:'Precision oncology kinase', needs:['In Vivo / Mouse Services','DMPK'], founded:2013, opportunity:'Medium — spinout programs active' },
  { name:'Arcellx', state:'CA', stage:'Phase II', focus:'CAR-T cell therapy', needs:['Bioanalysis','Protein Sciences / Biologics'], founded:2015, opportunity:'High — cell therapy bioanalysis demand' },

  // New Jersey (hub weight 9)
  { name:'Inhibrx Biosciences', state:'NJ', stage:'Phase II', focus:'Rare disease biologics', needs:['Protein Sciences / Biologics','Bioanalysis','Toxicology'], founded:2010, opportunity:'High — biologic tox & bioanalysis' },
  { name:'Day One Biopharmaceuticals', state:'NJ', stage:'Phase III', focus:'Pediatric oncology', needs:['In Vivo / Mouse Services','Toxicology','DMPK'], founded:2018, opportunity:'Medium — peds tox packages' },
  { name:'Kenvue Biotech spinouts', state:'NJ', stage:'Series A', focus:'Consumer health Rx crossover', needs:['ADME','CMC','Toxicology'], founded:2023, opportunity:'Medium — CMC and tox' },

  // North Carolina (hub weight 8)
  { name:'G1 Therapeutics', state:'NC', stage:'Commercial', focus:'Oncology supportive care', needs:['Bioanalysis','DMPK'], founded:2008, opportunity:'Medium — post-approval PK studies' },
  { name:'Talphera', state:'NC', stage:'Phase II', focus:'GI disorders', needs:['ADME','Bioanalysis','Toxicology'], founded:2017, opportunity:'Medium — GI ADME specialist' },
  { name:'Argos Therapeutics (revived)', state:'NC', stage:'Series A', focus:'Personalised immunotherapy', needs:['Protein Sciences / Biologics','Bioanalysis'], founded:2021, opportunity:'High — personalized medicine bioanalysis' },

  // Texas (hub weight 8)
  { name:'Entasis Therapeutics', state:'TX', stage:'Phase III', focus:'Antibiotic resistance', needs:['DMPK','Toxicology','Bioanalysis'], founded:2015, opportunity:'Medium — AMR program DMPK' },
  { name:'Iterion Therapeutics', state:'TX', stage:'Phase II', focus:'Oncology (GI)', needs:['In Vivo / Mouse Services','DMPK'], founded:2018, opportunity:'Medium — in vivo efficacy models' },
  { name:'Halo Dx', state:'TX', stage:'Series B', focus:'Diagnostics & oncology biomarkers', needs:['Biomarker / Genomics','Bioanalysis'], founded:2019, opportunity:'High — biomarker assay development' },

  // Pennsylvania (hub weight 7)
  { name:'Passage Bio', state:'PA', stage:'Phase I/II', focus:'Gene therapy, rare neurological', needs:['Toxicology','Bioanalysis','Protein Sciences / Biologics'], founded:2018, opportunity:'High — gene therapy tox packages' },
  { name:'Relay Biosciences', state:'PA', stage:'Series A', focus:'RNA therapeutics', needs:['DMPK','Toxicology','CMC'], founded:2021, opportunity:'High — RNA DMPK specialist gap' },
  { name:'Imvax', state:'PA', stage:'Phase II', focus:'Glioblastoma immunotherapy', needs:['Bioanalysis','In Vivo / Mouse Services'], founded:2012, opportunity:'Medium — CNS bioanalysis' },

  // New York (hub weight 7)
  { name:'Chinook Therapeutics', state:'NY', stage:'Phase III', focus:'Kidney disease', needs:['Bioanalysis','DMPK','Toxicology'], founded:2019, opportunity:'High — renal disease tox' },
  { name:'Prelude Therapeutics', state:'NY', stage:'Phase II', focus:'Epigenetic oncology', needs:['In Vivo / Mouse Services','DMPK'], founded:2016, opportunity:'Medium — epigenetic in vivo models' },

  // Maryland (hub weight 6)
  { name:'Emergent BioSolutions spinout', state:'MD', stage:'Series B', focus:'Infectious disease vaccines', needs:['Protein Sciences / Biologics','Bioanalysis','Toxicology'], founded:2022, opportunity:'High — vaccine bioanalysis' },
  { name:'Inhibix', state:'MD', stage:'Series A', focus:'Viral proteases', needs:['DMPK','ADME'], founded:2021, opportunity:'Medium — antiviral DMPK' },

  // Illinois (hub weight 6)
  { name:'Tempus AI Health', state:'IL', stage:'Commercial', focus:'AI-driven oncology diagnostics', needs:['Biomarker / Genomics','Bioanalysis'], founded:2015, opportunity:'High — genomics & biomarker assays' },
  { name:'Aravive', state:'IL', stage:'Phase III', focus:'Ovarian cancer', needs:['Bioanalysis','In Vivo / Mouse Services'], founded:2008, opportunity:'Medium — ovarian cancer in vivo' },

  // Washington (hub weight 6)
  { name:'Athira Pharma', state:'WA', stage:'Phase II', focus:'Neurodegeneration (AD)', needs:['DMPK','Bioanalysis','In Vivo / Mouse Services'], founded:2011, opportunity:'High — CNS DMPK & bioanalysis' },
  { name:'Chinook Biosciences', state:'WA', stage:'Series A', focus:'Renal inflammation', needs:['ADME','Toxicology'], founded:2022, opportunity:'Medium — early ADME tox' },

  // Colorado (hub weight 5)
  { name:'Bravura Biosciences', state:'CO', stage:'Series A', focus:'Autoimmune diseases', needs:['DMPK','Bioanalysis','Toxicology'], founded:2021, opportunity:'Medium — autoimmune tox' },

  // Minnesota (hub weight 5)
  { name:'Reshape Lifesciences', state:'MN', stage:'Commercial', focus:'Metabolic device/drug combo', needs:['ADME','Bioanalysis'], founded:2017, opportunity:'Medium — drug component ADME' },

  // Georgia (hub weight 4)
  { name:'Inhibrx (GA site)', state:'GA', stage:'Phase I', focus:'Oncology biologics', needs:['Protein Sciences / Biologics','Toxicology'], founded:2019, opportunity:'Medium — biologic tox' },

  // Virginia (hub weight 4)
  { name:'Xenotech Pharma', state:'VA', stage:'Series B', focus:'Organ-on-chip models', needs:['ADME','DMPK'], founded:2020, opportunity:'High — ADME/DMPK for novel platforms' },
];

const STAGE_COLORS = {
  'Phase III': '#2ecc71', 'Phase II': '#3b9eff', 'Phase I/II': '#3b9eff',
  'Phase I': '#9b59b6', 'Series B': '#e67e22', 'Series A': '#e74c3c',
  'Seed/Series A': '#e74c3c', 'Commercial': '#1abc9c', 'Platform': '#f39c12',
  'Acquired/spinout': '#95a5a6',
};

let clientStateFilter = '', clientStageFilter = '', clientNeedFilter = '';

function renderClients() {
  const pane = document.getElementById('tab-clients');
  if (!pane) return;

  // Build toolbar if not yet present
  if (!document.getElementById('clients-toolbar')) {
    // State options from data
    const states = [...new Set(POTENTIAL_CLIENTS.map(c => c.state))].sort();
    const stages = [...new Set(POTENTIAL_CLIENTS.map(c => c.stage))].sort();
    const needs  = [...new Set(POTENTIAL_CLIENTS.flatMap(c => c.needs))].sort();

    const toolbar = document.createElement('div');
    toolbar.id = 'clients-toolbar';
    toolbar.innerHTML = `
      <label>State</label>
      <select id="client-filter-state">
        <option value="">All States</option>
        ${states.map(s=>`<option>${s}</option>`).join('')}
      </select>
      <label>Stage</label>
      <select id="client-filter-stage">
        <option value="">All Stages</option>
        ${stages.map(s=>`<option>${s}</option>`).join('')}
      </select>
      <label>Service Need</label>
      <select id="client-filter-need">
        <option value="">All Services</option>
        ${needs.map(n=>`<option>${n}</option>`).join('')}
      </select>
      <span id="clients-count"></span>
    `;
    pane.appendChild(toolbar);

    const body = document.createElement('div');
    body.id = 'clients-body';
    pane.appendChild(body);

    toolbar.querySelector('#client-filter-state').addEventListener('change', e => { clientStateFilter = e.target.value; _renderClientCards(); });
    toolbar.querySelector('#client-filter-stage').addEventListener('change', e => { clientStageFilter = e.target.value; _renderClientCards(); });
    toolbar.querySelector('#client-filter-need').addEventListener('change',  e => { clientNeedFilter  = e.target.value; _renderClientCards(); });
  }

  _renderClientCards();
}

function _renderClientCards() {
  const body = document.getElementById('clients-body');
  const countEl = document.getElementById('clients-count');
  if (!body) return;

  // Get focal CRO's services to determine which clients are most relevant
  const focal = compareFocalId ? croData.cros.find(c => c.id === compareFocalId) : croData.cros.find(c => c.is_medicilon);
  const focalSvcs = new Set(focal ? (focal.services || []) : []);

  let filtered = POTENTIAL_CLIENTS.filter(c => {
    if (clientStateFilter && c.state !== clientStateFilter) return false;
    if (clientStageFilter && c.stage !== clientStageFilter) return false;
    if (clientNeedFilter && !c.needs.includes(clientNeedFilter)) return false;
    return true;
  });

  // Sort: clients whose needs overlap most with focal CRO first
  filtered.sort((a, b) => {
    const overlapA = a.needs.filter(n => focalSvcs.has(n)).length;
    const overlapB = b.needs.filter(n => focalSvcs.has(n)).length;
    const hwA = (croData.biotech_hub_weights || {})[a.state] || 0;
    const hwB = (croData.biotech_hub_weights || {})[b.state] || 0;
    return (overlapB * 10 + hwB) - (overlapA * 10 + hwA);
  });

  if (countEl) countEl.textContent = filtered.length + ' companies';
  body.innerHTML = '';

  filtered.forEach(c => {
    const overlap = c.needs.filter(n => focalSvcs.has(n));
    const missing = c.needs.filter(n => !focalSvcs.has(n));
    const matchScore = Math.round((overlap.length / c.needs.length) * 100);
    const stageColor = STAGE_COLORS[c.stage] || '#888';
    const hw = (croData.biotech_hub_weights || {})[c.state] || 0;

    const card = document.createElement('div');
    card.className = 'client-card';
    card.title = c.opportunity;
    card.innerHTML = `
      <div class="client-card-header">
        <div class="client-stage-dot" style="background:${stageColor}"></div>
        <div class="client-name">${c.name}</div>
        <div class="client-state-badge">${c.state}</div>
      </div>
      <div class="client-stage-label">${c.stage} · Founded ${c.founded} · Hub ${hw}/10</div>
      <div class="client-focus">${c.focus}</div>
      <div class="client-tags">
        ${overlap.map(n=>`<span class="client-tag need" title="Service match">✓ ${n}</span>`).join('')}
        ${missing.map(n=>`<span class="client-tag" title="Not in portfolio">${n}</span>`).join('')}
      </div>
      <div class="client-opportunity" title="Opportunity detail">
        Match ${matchScore}% · ${c.opportunity.split('—')[0].trim()}
      </div>
    `;
    card.addEventListener('click', () => {
      // Filter map to this state
      if (typeof openDetailPanel === 'function') openDetailPanel(c.state);
    });
    body.appendChild(card);
  });
}
"""

if 'function renderClients' not in html:
    html = html.replace('async function init(){', CLIENTS_JS + '\nasync function init(){', 1)
    changes.append("Added renderClients() + POTENTIAL_CLIENTS data")

# ── 7. Wire renderClients into renderBottomPanels ─────────────────────────────
OLD_BOTTOM = 'function renderBottomPanels(){renderOpportunities();renderWhitespace();renderUnderserved();initCompareTab();}'
NEW_BOTTOM = 'function renderBottomPanels(){renderOpportunities();renderWhitespace();renderUnderserved();initCompareTab();renderClients();}'
if OLD_BOTTOM in html:
    html = html.replace(OLD_BOTTOM, NEW_BOTTOM, 1)
    changes.append("Wired renderClients() into renderBottomPanels()")
else:
    OLD2 = 'function renderBottomPanels(){renderOpportunities();renderWhitespace();renderUnderserved();}'
    NEW2 = 'function renderBottomPanels(){renderOpportunities();renderWhitespace();renderUnderserved();renderClients();}'
    if OLD2 in html:
        html = html.replace(OLD2, NEW2, 1)
        changes.append("Wired renderClients() into renderBottomPanels() (alt)")

# ── 8. Re-render clients when compare pair changes ────────────────────────────
OLD_SET_COMPARE_END = '  renderCompareTab();\n}'
if 'renderClients' not in html.split('function setComparePair')[1][:500] if 'function setComparePair' in html else True:
    if OLD_SET_COMPARE_END in html:
        html = html.replace(OLD_SET_COMPARE_END,
            '  renderCompareTab();\n  _renderClientCards();\n}', 1)
        changes.append("Added _renderClientCards() call in setComparePair()")

# ── Write ─────────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"index.html: {original_len:,} -> {len(html):,} bytes\n")
for c in changes:
    print(f"  {'!!' if 'WARNING' in c else 'OK'} {c}")
