import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

original_len = len(html)
changes = []

# ────────────────────────────────────────────────────────────────────────────
# 1. Add a global state for the active compare pair
# ────────────────────────────────────────────────────────────────────────────
OLD_GLOBALS = "let croData=null,usGeo=null,activeServices=new Set(),allServices=[],croColors={},stateIndex={},selectedState=null,colorMode='density',mapProjection=null,mapSvgEl=null;"
NEW_GLOBALS  = OLD_GLOBALS + "\nlet compareFocalId=null,compareRivalId=null; // active compare pair"

if 'compareFocalId' not in html:
    html = html.replace(OLD_GLOBALS, NEW_GLOBALS, 1)
    changes.append("Added compareFocalId/compareRivalId globals")

# ────────────────────────────────────────────────────────────────────────────
# 2. Rewrite calcOpportunityScore / getMedicilonGaps / getUnderservedStates
#    to accept an optional focalId so they work for ANY company, not just Medicilon
# ────────────────────────────────────────────────────────────────────────────
OLD_CALC = """function calcOpportunityScore(abbr){
  const hw=(croData.biotech_hub_weights||{})[abbr]||0;
  const med=croData.cros.find(c=>c.is_medicilon),np=(med&&(med.states||[]).includes(abbr))?0:15;
  const ms=new Set(med?(med.core_services||med.services||[]):[]),cros=stateIndex[abbr]||[];
  let gs=0;ms.forEach(svc=>{const n=cros.filter(c=>c.services.includes(svc)).length;if(!n)gs+=10;else if(n===1)gs+=5;else if(n===2)gs+=2;});
  return Math.min(100,Math.round(hw*3+gs+np));
}"""

NEW_CALC = """function getFocal(focalId){
  if(focalId) return croData.cros.find(c=>c.id===focalId)||croData.cros.find(c=>c.is_medicilon);
  return croData.cros.find(c=>c.is_medicilon);
}
function calcOpportunityScore(abbr,focalId){
  const hw=(croData.biotech_hub_weights||{})[abbr]||0;
  const focal=getFocal(focalId);
  const np=(focal&&(focal.states||[]).includes(abbr))?0:15;
  const ms=new Set(focal?(focal.core_services||focal.services||[]):[]),cros=stateIndex[abbr]||[];
  let gs=0;ms.forEach(svc=>{const n=cros.filter(c=>c.services.includes(svc)).length;if(!n)gs+=10;else if(n===1)gs+=5;else if(n===2)gs+=2;});
  return Math.min(100,Math.round(hw*3+gs+np));
}"""

OLD_GAPS = """function getMedicilonGaps(abbr){
  const med=croData.cros.find(c=>c.is_medicilon),ms=new Set(med?(med.core_services||med.services||[]):[]);
  const cros=stateIndex[abbr]||[],gaps=[];
  ms.forEach(svc=>{const p=cros.filter(c=>c.services.includes(svc));
    if(!p.length)gaps.push(svc+': NO provider - strong entry opportunity');
    else if(p.length===1)gaps.push(svc+': Only 1 provider ('+p[0].short_name+') - underserved');
  });return gaps;
}"""

NEW_GAPS = """function getMedicilonGaps(abbr,focalId){
  const focal=getFocal(focalId),ms=new Set(focal?(focal.core_services||focal.services||[]):[]);
  const cros=stateIndex[abbr]||[],gaps=[];
  ms.forEach(svc=>{const p=cros.filter(c=>c.services.includes(svc));
    if(!p.length)gaps.push(svc+': NO provider - strong entry opportunity');
    else if(p.length===1)gaps.push(svc+': Only 1 provider ('+p[0].short_name+') - underserved');
  });return gaps;
}"""

OLD_TOP = """function getTopOpportunityStates(n){
  return Object.keys(STATE_NAMES).map(abbr=>({abbr,score:calcOpportunityScore(abbr),cros:stateIndex[abbr]||[],gaps:getMedicilonGaps(abbr)}))
    .filter(s=>s.score>0).sort((a,b)=>b.score-a.score).slice(0,n||5);
}"""

NEW_TOP = """function getTopOpportunityStates(n,focalId){
  const fid=focalId||compareFocalId;
  return Object.keys(STATE_NAMES).map(abbr=>({abbr,score:calcOpportunityScore(abbr,fid),cros:stateIndex[abbr]||[],gaps:getMedicilonGaps(abbr,fid)}))
    .filter(s=>s.score>0).sort((a,b)=>b.score-a.score).slice(0,n||5);
}"""

OLD_UNDERSERVED = """function getUnderservedStates(){
  const r=[],med=croData.cros.find(c=>c.is_medicilon),mc=new Set(med?(med.core_services||[]):[]);
  Object.keys(STATE_NAMES).forEach(abbr=>{
    const cros=stateIndex[abbr]||[],hw=(croData.biotech_hub_weights||{})[abbr]||0;
    if(hw<2)return;
    mc.forEach(svc=>{if(!activeServices.has(svc))return;const n=cros.filter(c=>c.services.includes(svc)).length;if(n<=1)r.push({abbr,svc,count:n,hubW:hw});});
  });
  return r.sort((a,b)=>b.hubW-a.hubW||a.count-b.count).slice(0,20);
}"""

NEW_UNDERSERVED = """function getUnderservedStates(focalId){
  const fid=focalId||compareFocalId;
  const r=[],focal=getFocal(fid),mc=new Set(focal?(focal.core_services||focal.services||[]):[]);
  Object.keys(STATE_NAMES).forEach(abbr=>{
    const cros=stateIndex[abbr]||[],hw=(croData.biotech_hub_weights||{})[abbr]||0;
    if(hw<2)return;
    mc.forEach(svc=>{if(!activeServices.has(svc))return;const n=cros.filter(c=>c.services.includes(svc)).length;if(n<=1)r.push({abbr,svc,count:n,hubW:hw});});
  });
  return r.sort((a,b)=>b.hubW-a.hubW||a.count-b.count).slice(0,20);
}"""

for old, new, label in [
    (OLD_CALC, NEW_CALC, "calcOpportunityScore"),
    (OLD_GAPS, NEW_GAPS, "getMedicilonGaps"),
    (OLD_TOP,  NEW_TOP,  "getTopOpportunityStates"),
    (OLD_UNDERSERVED, NEW_UNDERSERVED, "getUnderservedStates"),
]:
    if old in html:
        html = html.replace(old, new, 1)
        changes.append(f"Patched {label}() to accept focalId param")
    else:
        changes.append(f"WARNING: {label}() pattern not found")

# ────────────────────────────────────────────────────────────────────────────
# 3. Patch buildReasons() to use focal CRO
# ────────────────────────────────────────────────────────────────────────────
OLD_REASONS = """function buildReasons(item){
  const r=[],hw=(croData.biotech_hub_weights||{})[item.abbr]||0,med=croData.cros.find(c=>c.is_medicilon);
  if(hw>=8)r.push('Major biotech hub (weight: '+hw+'/10)');else if(hw>=5)r.push('Active biotech market (weight: '+hw+'/10)');
  if(!(med?(med.states||[]):[]).includes(item.abbr))r.push('No Medicilon presence - first-mover advantage');
  const ms=new Set(med?(med.core_services||[]):[]);let u=0,t=0;
  ms.forEach(svc=>{const n=item.cros.filter(c=>c.services.includes(svc)).length;if(!n)u++;else if(n===1)t++;});
  if(u)r.push(u+' Medicilon service(s) with zero local coverage');if(t)r.push(t+' service(s) with only 1 competitor');
  r.push(item.cros.length+' competitor CRO'+(item.cros.length!==1?'s':'')+' in state');return r.slice(0,4);
}"""

NEW_REASONS = """function buildReasons(item){
  const r=[],hw=(croData.biotech_hub_weights||{})[item.abbr]||0;
  const focal=getFocal(compareFocalId);
  const fName=focal?focal.short_name:'Focal CRO';
  if(hw>=8)r.push('Major biotech hub (weight: '+hw+'/10)');else if(hw>=5)r.push('Active biotech market (weight: '+hw+'/10)');
  if(!(focal?(focal.states||[]):[]).includes(item.abbr))r.push('No '+fName+' presence - first-mover advantage');
  const ms=new Set(focal?(focal.core_services||focal.services||[]):[]);let u=0,t=0;
  ms.forEach(svc=>{const n=item.cros.filter(c=>c.services.includes(svc)).length;if(!n)u++;else if(n===1)t++;});
  if(u)r.push(u+' '+fName+' service(s) with zero local coverage');if(t)r.push(t+' service(s) with only 1 competitor');
  r.push(item.cros.length+' competitor CRO'+(item.cros.length!==1?'s':'')+' in state');return r.slice(0,4);
}"""

if OLD_REASONS in html:
    html = html.replace(OLD_REASONS, NEW_REASONS, 1)
    changes.append("Patched buildReasons() to use focal CRO")

# ────────────────────────────────────────────────────────────────────────────
# 4. Add setComparePair() — called when selectors change, refreshes all tabs
# ────────────────────────────────────────────────────────────────────────────
SET_COMPARE_FN = """
// ─── Compare pair state — drives all bottom tabs ──────────────────────────────
function setComparePair(focalId, rivalId) {
  compareFocalId = focalId || null;
  compareRivalId = rivalId || null;

  // Update the bottom panel context label
  const focal = compareFocalId ? croData.cros.find(c => c.id === compareFocalId) : null;
  const rival = compareRivalId ? croData.cros.find(c => c.id === compareRivalId) : null;
  const label = document.getElementById('compare-context-label');
  if (label) {
    label.textContent = focal && rival
      ? `Showing: ${focal.short_name} vs ${rival.short_name}`
      : focal ? `Showing: ${focal.short_name} perspective`
      : 'Showing: All CROs';
    label.style.display = focal ? 'block' : 'none';
  }

  // Re-render all bottom tabs with new focal context
  renderOpportunities();
  renderWhitespace();
  renderUnderserved();
  renderCompareTab();
}
"""

if 'function setComparePair' not in html:
    html = html.replace('async function init(){', SET_COMPARE_FN + '\nasync function init(){', 1)
    changes.append("Added setComparePair() function")

# ────────────────────────────────────────────────────────────────────────────
# 5. Patch the compare modal selectors to call setComparePair on change
#    and add quick-select rival buttons
# ────────────────────────────────────────────────────────────────────────────
OLD_OPEN_COMPARE_START = "function openCompare() {\n  const overlay = document.getElementById('compare-modal-overlay');"

NEW_OPEN_COMPARE_START = """function openCompare() {
  const overlay = document.getElementById('compare-modal-overlay');"""

# Find openCompare and patch the selector onChange inside it
OLD_SELECTOR_WIRE = "    sel.onchange = renderCompareTable;"
NEW_SELECTOR_WIRE = """    sel.addEventListener('change', () => {
      const a = document.getElementById('compare-modal-a');
      const b = document.getElementById('compare-modal-b');
      if (a && b) setComparePair(a.value, b.value);
      renderCompareTable();
      // Sync quick buttons
      populateQuickBtns();
    });"""

if OLD_SELECTOR_WIRE in html:
    html = html.replace(OLD_SELECTOR_WIRE, NEW_SELECTOR_WIRE, 1)
    changes.append("Wired modal selectors -> setComparePair()")

# ────────────────────────────────────────────────────────────────────────────
# 6. Rename modal select IDs to compare-modal-a/b for clarity
#    and add quick-rival buttons row + context label to bottom panel
# ────────────────────────────────────────────────────────────────────────────

# Find modal HTML selectors and rename IDs
# The modal selectors currently use .compare-select-input without IDs
# Find the compare-modal HTML block
modal_sel_start = html.find('<div id="compare-modal-overlay"')
modal_sel_end   = html.find('</div>', html.find('</div>', modal_sel_start) + 1)

# Check if IDs already added
if 'id="compare-modal-a"' not in html:
    # Find the two .compare-select-input elements inside the modal
    # They look like: <select class="compare-select-input" ...>
    idx = html.find('compare-select-input', modal_sel_start)
    if idx > 0:
        # Find the actual <select tag before it
        tag_start = html.rfind('<select', 0, idx)
        # Add id="compare-modal-a"
        old_sel = html[tag_start:html.find('>', tag_start)+1]
        new_sel = old_sel.replace('<select', '<select id="compare-modal-a"', 1)
        html = html.replace(old_sel, new_sel, 1)
        # Second select
        idx2 = html.find('compare-select-input', idx + 50)
        tag_start2 = html.rfind('<select', 0, idx2)
        old_sel2 = html[tag_start2:html.find('>', tag_start2)+1]
        new_sel2 = old_sel2.replace('<select', '<select id="compare-modal-b"', 1)
        html = html.replace(old_sel2, new_sel2, 1)
        changes.append("Added id=compare-modal-a/b to modal selects")

# ────────────────────────────────────────────────────────────────────────────
# 7. Add quick-rival buttons and context label into modal
# ────────────────────────────────────────────────────────────────────────────
QUICK_BTNS_HTML = """
  <!-- Quick rival buttons -->
  <div id="compare-quick-row" style="padding:8px 20px;border-bottom:1px solid var(--border);display:flex;gap:6px;flex-wrap:wrap;flex-shrink:0">
    <span style="font-size:10px;color:var(--text-dim);align-self:center;margin-right:4px">Quick compare vs:</span>
  </div>
"""

POPULATE_QUICK_JS = """
function populateQuickBtns() {
  const row = document.getElementById('compare-quick-row');
  if (!row || !croData) return;
  const selA = document.getElementById('compare-modal-a');
  const focalId = selA ? selA.value : '';

  // Remove old buttons (keep the label span)
  Array.from(row.querySelectorAll('.quick-rival-btn')).forEach(b => b.remove());

  // Add top 4 rivals (not the focal itself)
  const rivals = croData.cros.filter(c => c.id !== focalId && !c.is_medicilon).slice(0, 4);
  rivals.forEach(r => {
    const btn = document.createElement('button');
    btn.className = 'quick-rival-btn';
    btn.textContent = 'vs ' + r.short_name;
    btn.onclick = () => {
      const selB = document.getElementById('compare-modal-b');
      if (selB) { selB.value = r.id; }
      setComparePair(focalId, r.id);
      renderCompareTable();
      populateQuickBtns();
    };
    row.appendChild(btn);
  });
}
"""

QUICK_BTN_CSS = """
.quick-rival-btn {
  background: var(--surface2); border: 1px solid var(--border); border-radius: 20px;
  padding: 4px 12px; color: var(--text-muted); font-size: 11px; cursor: pointer;
  font-family: var(--font-body); transition: all 0.15s; white-space: nowrap;
}
.quick-rival-btn:hover { border-color: var(--accent); color: var(--accent); background: rgba(59,158,255,0.08); }
#compare-context-label {
  display: none; font-size: 10px; color: var(--gold); font-weight: 600;
  padding: 3px 10px; background: var(--gold-dim); border: 1px solid var(--gold-border);
  border-radius: 4px; margin-left: auto;
}
"""

# Add quick buttons into modal HTML
if 'compare-quick-row' not in html:
    OLD_COMPARE_BODY = '<div id="compare-modal-body"></div>'
    NEW_COMPARE_BODY = QUICK_BTNS_HTML + '\n  <div id="compare-modal-body"></div>'
    if OLD_COMPARE_BODY in html:
        html = html.replace(OLD_COMPARE_BODY, NEW_COMPARE_BODY, 1)
        changes.append("Added quick-rival buttons row to compare modal")

# Add context label to bottom tab bar
if 'compare-context-label' not in html:
    OLD_BOTTOM_TABS_END = '</div>\n      <div id="bottom-content">'
    NEW_BOTTOM_TABS_END = '  <span id="compare-context-label"></span>\n      </div>\n      <div id="bottom-content">'
    if OLD_BOTTOM_TABS_END in html:
        html = html.replace(OLD_BOTTOM_TABS_END, NEW_BOTTOM_TABS_END, 1)
        changes.append("Added compare-context-label to bottom tab bar")

# Add CSS
if '.quick-rival-btn' not in html:
    html = html.replace('</style>', QUICK_BTN_CSS + '\n</style>', 1)
    changes.append("Added quick-rival-btn and context-label CSS")

# Add JS functions
if 'function populateQuickBtns' not in html:
    html = html.replace('function setComparePair', POPULATE_QUICK_JS + '\nfunction setComparePair', 1)
    changes.append("Added populateQuickBtns() function")

# ────────────────────────────────────────────────────────────────────────────
# 8. Patch openCompare() to call populateQuickBtns + setComparePair on open
# ────────────────────────────────────────────────────────────────────────────
OLD_OVERLAY_SHOW = "  overlay.classList.add('visible');\n  renderCompareTable();\n}"
NEW_OVERLAY_SHOW = (
    "  overlay.classList.add('visible');\n"
    "  populateQuickBtns();\n"
    "  const ma = document.getElementById('compare-modal-a');\n"
    "  const mb = document.getElementById('compare-modal-b');\n"
    "  if (ma && mb) setComparePair(ma.value, mb.value);\n"
    "  renderCompareTable();\n"
    "}"
)
if OLD_OVERLAY_SHOW in html:
    html = html.replace(OLD_OVERLAY_SHOW, NEW_OVERLAY_SHOW, 1)
    changes.append("Patched openCompare() to call setComparePair on open")

# ────────────────────────────────────────────────────────────────────────────
# 9. Patch initCompareTab selects to also call setComparePair
# ────────────────────────────────────────────────────────────────────────────
OLD_TAB_CHANGE = "    sel.addEventListener('change', renderCompareTab);"
NEW_TAB_CHANGE = """    sel.addEventListener('change', () => {
      const ta = document.getElementById('compare-tab-a');
      const tb = document.getElementById('compare-tab-b');
      if (ta && tb) setComparePair(ta.value, tb.value);
      renderCompareTab();
    });"""
if OLD_TAB_CHANGE in html:
    html = html.replace(OLD_TAB_CHANGE, NEW_TAB_CHANGE, 1)
    changes.append("Patched compare tab selects -> setComparePair()")

# ────────────────────────────────────────────────────────────────────────────
# Write
# ────────────────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"index.html: {original_len:,} -> {len(html):,} bytes\n")
for c in changes:
    print(f"  {'!!' if 'WARNING' in c else 'OK'} {c}")
