"""Patch index.html: add getStateDominantColor, hexWithAlpha, renderLegendSwatches,
update legend HTML, wire up renderLegendSwatches in init()."""

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# ── 1. Replace old legend HTML ────────────────────────────────────────────────
OLD_LEGEND = '''      <!-- Legend -->
      <div id="map-legend">
        <div class="legend-title">CRO Density per State</div>
        <div class="legend-scale">
          <div>
            <div class="legend-bar"></div>
            <div class="legend-labels"><span>0</span><span id="legend-max">12</span></div>
          </div>
        </div>
        <div class="legend-medicilon">
          <div class="legend-medicilon-line"></div>
          <span>Medicilon presence (future target)</span>
        </div>
      </div>'''

NEW_LEGEND = '''      <!-- Legend -->
      <div id="map-legend">
        <div class="legend-title">Dominant Service per State</div>
        <div id="legend-swatches" style="display:flex;flex-wrap:wrap;gap:4px;max-width:210px;margin-top:6px"></div>
        <div class="legend-medicilon" style="margin-top:8px">
          <div class="legend-medicilon-line"></div>
          <span>Medicilon (future target)</span>
        </div>
      </div>'''

if OLD_LEGEND in html:
    html = html.replace(OLD_LEGEND, NEW_LEGEND, 1)
    print("OK: Legend HTML updated")
else:
    print("WARNING: Legend HTML not found — skipping")

# ── 2. Inject helper functions before renderMap() ─────────────────────────────
COLOR_HELPERS = """
function hexWithAlpha(hex, alpha) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  const br=26, bg=41, bb=55; // dark bg #1a2937
  return 'rgb(' + Math.round(br+(r-br)*alpha) + ',' + Math.round(bg+(g-bg)*alpha) + ',' + Math.round(bb+(b-bb)*alpha) + ')';
}

function getStateDominantColor(abbr) {
  const cros = getActiveCrosForState(abbr);
  if (!cros || cros.length === 0) return '#1a2937';
  const svcCount = {};
  cros.forEach(function(cro) {
    (cro.services || []).forEach(function(s) {
      if (activeServices.has(s)) svcCount[s] = (svcCount[s] || 0) + 1;
    });
  });
  const entries = Object.entries(svcCount).sort(function(a,b){ return b[1]-a[1]; });
  if (!entries.length) return '#1a2937';
  const dominant = entries[0][0];
  const baseColor = SERVICE_COLORS[dominant] || '#3b9eff';
  const intensity = Math.min(1, 0.35 + cros.length * 0.15);
  return hexWithAlpha(baseColor, intensity);
}

function renderLegendSwatches() {
  const container = document.getElementById('legend-swatches');
  if (!container) return;
  container.innerHTML = '';
  Object.entries(SERVICE_COLORS).forEach(function(entry) {
    const svc = entry[0], color = entry[1];
    const item = document.createElement('div');
    item.style.cssText = 'display:flex;align-items:center;gap:3px;font-size:9px;color:var(--text-muted);white-space:nowrap';
    const dot = document.createElement('span');
    dot.style.cssText = 'width:8px;height:8px;border-radius:2px;background:' + color + ';flex-shrink:0';
    item.appendChild(dot);
    item.appendChild(document.createTextNode(svc.split('/')[0].trim()));
    container.appendChild(item);
  });
}

"""

RENDERMAPFN = 'function renderMap() {'
if RENDERMAPFN in html:
    html = html.replace(RENDERMAPFN, COLOR_HELPERS + RENDERMAPFN, 1)
    print("OK: Color helper functions injected before renderMap()")
else:
    print("WARNING: renderMap() not found")

# ── 3. Replace fill logic in renderMap() — initial draw ──────────────────────
OLD_FILL_INIT = """.attr('fill', d => {
      const abbr = FIPS_TO_STATE[d.id.toString().padStart(2, '0')];
      const count = getActiveCrosForState(abbr).length;
      return count === 0 ? '#1a2937' : colorScale(count);
    })"""

NEW_FILL_INIT = """.attr('fill', d => {
      const abbr = FIPS_TO_STATE[d.id.toString().padStart(2, '0')];
      return getStateDominantColor(abbr);
    })"""

if OLD_FILL_INIT in html:
    html = html.replace(OLD_FILL_INIT, NEW_FILL_INIT, 1)
    print("OK: renderMap() fill logic replaced")
else:
    print("WARNING: renderMap() fill logic not found (may already be patched)")

# ── 4. Replace fill logic in updateMapColors() ───────────────────────────────
OLD_FILL_UPDATE = """.attr('fill', d => {
      const abbr = FIPS_TO_STATE[d.id.toString().padStart(2, '0')];
      const count = getActiveCrosForState(abbr).length;
      return count === 0 ? '#1a2937' : colorScale(count);
    })"""

NEW_FILL_UPDATE = """.attr('fill', d => {
      const abbr = FIPS_TO_STATE[d.id.toString().padStart(2, '0')];
      return getStateDominantColor(abbr);
    })"""

if OLD_FILL_UPDATE in html:
    html = html.replace(OLD_FILL_UPDATE, NEW_FILL_UPDATE, 1)
    print("OK: updateMapColors() fill logic replaced")
else:
    print("INFO: updateMapColors() fill logic not found separately (may share same block)")

# ── 5. Call renderLegendSwatches() in init() after renderSidebar() ───────────
OLD_INIT_LINE = "renderSidebar();"
NEW_INIT_LINE = "renderSidebar();\n    renderLegendSwatches();"
if OLD_INIT_LINE in html:
    html = html.replace(OLD_INIT_LINE, NEW_INIT_LINE, 1)
    print("OK: renderLegendSwatches() wired into init()")
else:
    print("WARNING: renderSidebar() call not found in init()")

# ── 6. Write ──────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Size:', len(html), 'bytes')
print('Has getStateDominantColor:', 'getStateDominantColor' in html)
print('Has renderLegendSwatches:', 'renderLegendSwatches' in html)
