/**
 * Market Map Page — Interactive US choropleth with CRO coverage analysis
 * Ported from the original index.html, restructured for full-screen use.
 */
const PageMap = {
  // Internal state
  colorMode: 'density',
  activeServices: new Set(),
  selectedState: null,
  allServices: [],
  stateIndex: {},
  croColors: {},
  mapProjection: null,
  mapSvgEl: null,
  usGeo: null,

  render(container) {
    const data = App.croData;
    if (!data) {
      container.innerHTML = '<div class="empty-state"><div class="empty-state-title">No data</div></div>';
      return;
    }

    this.allServices = data.service_categories || [];
    this.activeServices = new Set(this.allServices);

    // Color assignments
    data.cros.filter(c => !c.is_medicilon).forEach((c, i) => {
      this.croColors[c.id] = CRO_COLORS[i % (CRO_COLORS.length - 1)];
    });
    const med = data.cros.find(c => c.is_medicilon);
    if (med) this.croColors[med.id] = '#f5a623';

    // State index
    this.stateIndex = {};
    data.cros.forEach(cro => {
      if (cro.is_medicilon) return;
      (cro.states || []).forEach(st => {
        if (!this.stateIndex[st]) this.stateIndex[st] = [];
        this.stateIndex[st].push(cro);
      });
    });

    container.innerHTML = `
      <div class="page-header flex-between">
        <div>
          <div class="page-title">Market Map</div>
          <div class="page-subtitle">Competitive CRO coverage across US biotech hubs</div>
        </div>
        <div class="flex-center gap-8">
          <div class="tab-bar" id="map-modes" style="margin:0;padding:0;border:none">
            <button class="tab-btn active" data-mode="density">Service Mix</button>
            <button class="tab-btn" data-mode="coverage">CRO Density</button>
            <button class="tab-btn" data-mode="service">Service Coverage</button>
          </div>
        </div>
      </div>

      <div class="grid-2col" style="grid-template-columns: 1fr 300px;">
        <!-- Map Area -->
        <div style="position:relative">
          <div id="map-container" style="position:relative;width:100%;height:70vh;background:var(--bg-deep);border-radius:var(--radius);border:1px solid var(--border-soft);overflow:hidden">
            <svg id="us-map"></svg>
            <div id="map-legend"></div>
            <div id="map-stats"></div>
          </div>
          <!-- Detail panel overlay -->
          <div id="detail-panel" class="hidden"></div>
        </div>

        <!-- Sidebar: Filters -->
        <div style="display:flex;flex-direction:column;gap:14px">
          <div class="card">
            <div class="card-title mb-12">Service Filters</div>
            <div id="service-filters" style="max-height:300px;overflow-y:auto"></div>
            <div style="display:flex;gap:6px;margin-top:10px">
              <button class="btn btn-sm" id="select-all-btn">All</button>
              <button class="btn btn-sm" id="clear-all-btn">None</button>
              <button class="btn btn-sm btn-gold" id="medicilon-btn">Medicilon Core</button>
            </div>
          </div>
          <div class="card">
            <div class="card-title mb-12">CRO Companies</div>
            <div id="company-list"></div>
          </div>
        </div>
      </div>
    `;

    this.setupFilters();
    this.renderCompanyList();
    this.loadMap();
  },

  setupFilters() {
    const container = document.getElementById('service-filters');
    if (!container) return;

    this.allServices.forEach(svc => {
      const col = SERVICE_COLORS[svc] || '#888';
      const id = 'svc-' + svc.replace(/[^a-zA-Z0-9]/g, '_');
      const div = document.createElement('div');
      div.style.cssText = 'display:flex;align-items:center;gap:8px;padding:4px 0;cursor:pointer;font-size:12px';
      div.innerHTML = `<input type="checkbox" id="${id}" checked style="accent-color:${col};cursor:pointer">
        <span style="width:8px;height:8px;border-radius:2px;background:${col};flex-shrink:0"></span>
        <label for="${id}" style="cursor:pointer;flex:1;font-size:12px">${svc}</label>`;
      div.querySelector('input').addEventListener('change', (e) => {
        if (e.target.checked) this.activeServices.add(svc);
        else this.activeServices.delete(svc);
        this.updateMap();
      });
      container.appendChild(div);
    });

    document.getElementById('select-all-btn')?.addEventListener('click', () => {
      this.activeServices = new Set(this.allServices);
      container.querySelectorAll('input').forEach(i => i.checked = true);
      this.updateMap();
    });
    document.getElementById('clear-all-btn')?.addEventListener('click', () => {
      this.activeServices = new Set();
      container.querySelectorAll('input').forEach(i => i.checked = false);
      this.updateMap();
    });
    document.getElementById('medicilon-btn')?.addEventListener('click', () => {
      const med = App.croData.cros.find(c => c.is_medicilon);
      const core = new Set(med ? (med.core_services || med.services || []) : []);
      this.activeServices = core;
      container.querySelectorAll('div').forEach(item => {
        const inp = item.querySelector('input');
        const lbl = item.querySelector('label');
        if (inp && lbl) inp.checked = core.has(lbl.textContent);
      });
      this.updateMap();
    });

    // Mode toggle
    document.querySelectorAll('#map-modes .tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#map-modes .tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.colorMode = btn.dataset.mode;
        this.updateMapColors();
        this.updateLegend();
      });
    });
  },

  renderCompanyList() {
    const el = document.getElementById('company-list');
    if (!el) return;

    const data = App.croData;
    el.innerHTML = (data.cros || []).map(cro => {
      const col = this.croColors[cro.id] || '#888';
      const sc = cro.is_medicilon ? '—' : (cro.states || []).length;
      const badges = (cro.services || []).slice(0, 5).map(s => {
        const c = SERVICE_COLORS[s] || '#888';
        return `<span style="font-size:9px;padding:1px 4px;border-radius:2px;background:${c}22;border:1px solid ${c}44;color:${c}">${s.split(' / ')[0].split(' ')[0]}</span>`;
      }).join('');

      return `
        <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border-dim);cursor:pointer;font-size:12px"
             class="${cro.is_medicilon ? '' : ''}"
             onclick="PageMap.openCroModal('${cro.id}')">
          <span style="width:10px;height:10px;border-radius:50%;background:${col};flex-shrink:0"></span>
          <span style="flex:1;font-weight:500">${cro.short_name}</span>
          <span style="color:var(--text-dim);font-size:10px">${sc} states</span>
        </div>
      `;
    }).join('');
  },

  // ── Map Rendering ──────────────────────────────────────────────────────────
  async loadMap() {
    const data = App.croData;
    if (!data) return;

    // Load TopoJSON
    if (!this.usGeo) {
      try {
        this.usGeo = await d3.json('data/states-10m.json');
      } catch (e) {
        console.warn('Could not load TopoJSON, map unavailable');
        return;
      }
    }

    this.renderD3Map();
    this.updateStats();
  },

  getActiveCros(st) {
    if (!this.activeServices.size) return [];
    return (this.stateIndex[st] || []).filter(c =>
      c.services.some(s => this.activeServices.has(s))
    );
  },

  getDominantService(st) {
    const counts = {};
    this.getActiveCros(st).forEach(cro =>
      cro.services.forEach(s => {
        if (this.activeServices.has(s)) counts[s] = (counts[s] || 0) + 1;
      })
    );
    let best = null, bestN = 0;
    Object.entries(counts).forEach(([s, n]) => { if (n > bestN) { bestN = n; best = s; } });
    return best;
  },

  getStateColor(abbr, maxCros) {
    const count = this.getActiveCros(abbr).length;
    // Biophilic no-data color: warm sandy beige
    const noData = '#e0d8c8';
    if (!count) return noData;

    if (this.colorMode === 'density') {
      const dom = this.getDominantService(abbr);
      const col = SERVICE_COLORS[dom] || '#5d9e68';
      return d3.interpolate(noData, col)(Math.min(0.25 + (count / Math.max(maxCros, 1)) * 0.75, 1));
    } else if (this.colorMode === 'service') {
      if (this.activeServices.size !== 1) {
        return d3.scaleSequential().domain([0, maxCros]).interpolator(d3.interpolate(noData, '#4a8254'))(count);
      }
      const col = SERVICE_COLORS[[...this.activeServices][0]] || '#5d9e68';
      return d3.interpolate(noData, col)(Math.min(0.2 + (count / Math.max(maxCros, 1)) * 0.8, 1));
    }
    return d3.scaleSequential().domain([0, maxCros]).interpolator(d3.interpolate(noData, '#4a8254'))(count);
  },

  renderD3Map() {
    const container = document.getElementById('map-container');
    const svg = d3.select('#us-map');
    const w = container.clientWidth;
    const h = container.clientHeight;

    svg.selectAll('*').remove();
    svg.attr('viewBox', `0 0 ${w} ${h}`);

    const proj = d3.geoAlbersUsa().fitSize([w, h], topojson.feature(this.usGeo, this.usGeo.objects.states));
    this.mapProjection = proj;
    this.mapSvgEl = svg;

    const path = d3.geoPath().projection(proj);
    const states = topojson.feature(this.usGeo, this.usGeo.objects.states).features;
    const maxCros = d3.max(states, d => this.getActiveCros(this.fipsToState(d.id)).length) || 1;

    const FIPS_TO_STATE = {"01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV","55":"WI","56":"WY"};
    this.FIPS_TO_STATE = FIPS_TO_STATE;

    const self = this;

    const g = svg.append('g').attr('class', 'states');

    g.selectAll('path.state-path')
      .data(states)
      .enter().append('path')
      .attr('class', 'state-path')
      .attr('d', path)
      .attr('fill', d => self.getStateColor(FIPS_TO_STATE[d.id.toString().padStart(2, '0')], maxCros))
      .attr('stroke', '#b8a890')
      .attr('stroke-width', 0.5)
      .style('cursor', 'pointer')
      .on('mouseenter', function(ev, d) {
        d3.select(this)
          .attr('stroke', '#5c4a3a')
          .attr('stroke-width', 1.5)
          .style('opacity', 0.95);
        self.showTooltip(ev, FIPS_TO_STATE[d.id.toString().padStart(2, '0')]);
      })
      .on('mouseleave', function() {
        d3.select(this)
          .attr('stroke', '#b8a890')
          .attr('stroke-width', 0.5)
          .style('opacity', 1);
        self.hideTooltip();
      })
      .on('click', (ev, d) => {
        ev.stopPropagation();
        self.openDetail(FIPS_TO_STATE[d.id.toString().padStart(2, '0')]);
      });

    // State borders (mesh)
    svg.append('path')
      .attr('fill', 'none')
      .attr('stroke', '#b8a890')
      .attr('stroke-width', 0.5)
      .attr('d', path(topojson.mesh(this.usGeo, this.usGeo.objects.states, (a, b) => a !== b)));

    // Click background to deselect
    svg.on('click', () => {
      this.selectedState = null;
      this.updateMapColors();
      document.getElementById('detail-panel')?.classList.add('hidden');
    });

    // Resize
    window.addEventListener('resize', () => {
      if (App.currentPage !== 'map') return;
      const nw = container.clientWidth, nh = container.clientHeight;
      svg.attr('viewBox', `0 0 ${nw} ${nh}`);
      proj.fitSize([nw, nh], topojson.feature(this.usGeo, this.usGeo.objects.states));
      path.projection(proj);
      svg.selectAll('path.state-path').attr('d', path);
    });

    this.updateLegend();
    this.updateStats();
  },

  fipsToState(fipsId) {
    return this.FIPS_TO_STATE?.[fipsId.toString().padStart(2, '0')] || '??';
  },

  // ── Tooltip ────────────────────────────────────────────────────────────────
  showTooltip(ev, st) {
    let tooltip = document.getElementById('map-tooltip');
    if (!tooltip) {
      tooltip = document.createElement('div');
      tooltip.id = 'map-tooltip';
      tooltip.style.cssText = `
        position:fixed;background:var(--surface);border:1px solid var(--border-soft);
        border-radius:var(--radius-sm);padding:12px 14px;pointer-events:none;z-index:2000;
        min-width:200px;max-width:300px;box-shadow:var(--shadow-earth);
        font-size:12px;color:var(--text-soft);
      `;
      document.body.appendChild(tooltip);
    }

    const cros = this.getActiveCros(st);
    const STATE_NAMES = {"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"};

    tooltip.innerHTML = `
      <div style="font-size:14px;font-weight:600;margin-bottom:4px;color:var(--moss-deep)">${STATE_NAMES[st] || st}</div>
      <div style="color:var(--text-dim);margin-bottom:8px">${cros.length} active CROs</div>
      <div style="display:flex;flex-direction:column;gap:2px">
        ${cros.slice(0, 8).map(c => {
          const col = this.croColors[c.id] || '#888';
          return `<div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text-soft)">
            <span style="width:7px;height:7px;border-radius:50%;background:${col}"></span>${c.short_name}
          </div>`;
        }).join('')}
        ${cros.length > 8 ? `<div style="font-size:10px;color:var(--text-dim)">+${cros.length - 8} more</div>` : ''}
      </div>
      <div style="margin-top:6px;font-size:10px;color:var(--text-dim)">Click for details</div>
    `;

    tooltip.style.left = (ev.clientX + 14) + 'px';
    tooltip.style.top = (ev.clientY - 10) + 'px';
    tooltip.style.display = 'block';
  },

  hideTooltip() {
    const tooltip = document.getElementById('map-tooltip');
    if (tooltip) tooltip.style.display = 'none';
  },

  // ── Detail Panel ───────────────────────────────────────────────────────────
  openDetail(st) {
    this.selectedState = st;
    this.updateMapColors();

    const panel = document.getElementById('detail-panel');
    if (!panel) return;

    const cros = this.getActiveCros(st);
    const STATE_NAMES = {"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"};
    const med = App.croData.cros.find(c => c.is_medicilon);
    const medSvcs = new Set(med?.core_services || med?.services || []);

    // Service coverage in this state
    const svcCoverage = {};
    cros.forEach(cro => {
      (cro.services || []).forEach(s => { svcCoverage[s] = (svcCoverage[s] || 0) + 1; });
    });

    panel.innerHTML = `
      <div style="padding:16px">
        <div class="flex-between mb-12">
          <div class="card-title" style="font-size:16px">${STATE_NAMES[st] || st}</div>
          <button style="background:none;border:none;color:var(--text-dim);font-size:18px;cursor:pointer" onclick="document.getElementById('detail-panel').classList.add('hidden')">✕</button>
        </div>
        <div style="font-size:12px;color:var(--text-dim);margin-bottom:12px">${cros.length} CROs · ${Object.keys(svcCoverage).length} services covered</div>

        <div class="card-title mb-8" style="font-size:12px">CROs Present</div>
        ${cros.map(c => {
          const col = this.croColors[c.id] || '#888';
          return `<div style="display:flex;align-items:center;gap:8px;padding:6px 0;font-size:12px;border-bottom:1px solid var(--border-dim)">
            <span style="width:8px;height:8px;border-radius:50%;background:${col}"></span>
            <span style="flex:1">${c.short_name}</span>
            <span class="tag tag-default">Tier ${c.tier || '-'}</span>
          </div>`;
        }).join('')}

        <div class="card-title mb-8 mt-12" style="font-size:12px">Service Coverage</div>
        ${App.croData.service_categories.map(s => {
          const cnt = svcCoverage[s] || 0;
          const isMed = medSvcs.has(s);
          const col = SERVICE_COLORS[s] || '#888';
          return `
            <div class="flex-between" style="padding:4px 0;font-size:11px">
              <span style="display:flex;align-items:center;gap:6px">
                <span style="width:6px;height:6px;border-radius:2px;background:${col}"></span>
                ${s} ${isMed ? '<span style="color:var(--gold);font-size:10px">(Medicilon)</span>' : ''}
              </span>
              <span style="color:${cnt === 0 ? 'var(--red)' : cnt === 1 ? 'var(--orange)' : 'var(--green)'}">
                ${cnt === 0 ? 'Gap' : `${cnt} CRO${cnt>1?'s':''}`}
              </span>
            </div>
          `;
        }).join('')}
      </div>
    `;

    panel.classList.remove('hidden');
    panel.style.cssText = `
      position:absolute;top:8px;right:8px;bottom:8px;width:300px;
      background:var(--surface);border:1px solid var(--border);
      border-radius:var(--radius);overflow-y:auto;z-index:50;
      box-shadow:var(--shadow-md);
    `;
  },

  openCroModal(croId) {
    const cro = App.croData.cros.find(c => c.id === croId);
    if (!cro) return;

    const sc = SERVICE_COLORS;
    const badges = (cro.services || []).map(s => {
      const c = sc[s] || '#888';
      return `<span class="tag" style="background:${c}22;border-color:${c}44;color:${c}">${s}</span>`;
    }).join(' ');

    App.openModal(cro.name, `
      <div class="flex-between mb-12">
        <span class="tag tag-gold">Tier ${cro.tier || '-'}</span>
        <span class="text-dim">${cro.states?.length || 0} US states</span>
      </div>
      <p style="font-size:13px;color:var(--text-muted);line-height:1.6;margin-bottom:12px">${cro.description || cro.summary || 'No description available.'}</p>
      ${cro.website_url ? `<p class="mb-12"><a href="${cro.website_url}" target="_blank">🌐 ${cro.website_url}</a></p>` : ''}
      <div class="card-title mb-8">Services (${cro.services?.length || 0})</div>
      <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px">${badges}</div>
      ${cro.states?.length ? `
        <div class="card-title mb-8">US Presence</div>
        <div style="display:flex;flex-wrap:wrap;gap:4px">${cro.states.map(s => `<span class="tag tag-default">${s}</span>`).join('')}</div>
      ` : ''}
    `);
  },

  // ── Map Updates ────────────────────────────────────────────────────────────
  updateMap() {
    this.updateMapColors();
    this.updateLegend();
    this.updateStats();
  },

  updateMapColors() {
    const svg = d3.select('#us-map');
    if (!svg || !this.usGeo) return;

    const states = topojson.feature(this.usGeo, this.usGeo.objects.states).features;
    const maxCros = d3.max(states, d => this.getActiveCros(this.fipsToState(d.id)).length) || 1;
    const self = this;

    svg.selectAll('path.state-path')
      .data(states)
      .transition().duration(300)
      .attr('fill', d => self.getStateColor(self.fipsToState(d.id), maxCros))
      .attr('stroke', d => self.fipsToState(d.id) === self.selectedState ? '#5c4a3a' : '#b8a890')
      .attr('stroke-width', d => self.fipsToState(d.id) === self.selectedState ? 2 : 0.5);
  },

  updateStats() {
    const el = document.getElementById('map-stats');
    if (!el) return;

    const cros = App.croData?.cros?.filter(c => !c.is_medicilon) || [];
    const stateSet = new Set();
    cros.forEach(c => (c.states || []).forEach(s => stateSet.add(s)));

    el.innerHTML = `
      <div class="stat-chip"><div class="stat-val">${cros.length}</div><div class="stat-label">CROs Mapped</div></div>
      <div class="stat-chip"><div class="stat-val">${stateSet.size}</div><div class="stat-label">States Covered</div></div>
    `;
    el.style.cssText = 'position:absolute;top:12px;right:12px;display:flex;gap:8px';
    el.querySelectorAll('.stat-chip').forEach(ch => {
      ch.style.cssText = 'background:var(--surface);border:1px solid var(--border-soft);border-radius:var(--radius-sm);padding:8px 12px;text-align:center;box-shadow:var(--shadow-soft)';
    });
    el.querySelectorAll('.stat-val').forEach(v => {
      v.style.cssText = 'font-size:18px;font-weight:700;color:var(--moss)';
    });
    el.querySelectorAll('.stat-label').forEach(l => {
      l.style.cssText = 'font-size:10px;color:var(--text-soft)';
    });
  },

  updateLegend() {
    const el = document.getElementById('map-legend');
    if (!el) return;

    let title, content;
    if (this.colorMode === 'density') {
      title = 'Service Mix';
      const covered = this.allServices.filter(s =>
        this.activeServices.has(s) &&
        Object.values(this.stateIndex).some(cros => cros.some(c => c.services.includes(s)))
      );
      content = covered.map(s => `
        <div style="display:flex;align-items:center;gap:6px;font-size:10px;margin:2px 0;color:var(--text-soft)">
          <span style="width:10px;height:10px;border-radius:2px;background:${SERVICE_COLORS[s]||'#888'}"></span>${s}
        </div>
      `).join('');
    } else if (this.colorMode === 'service') {
      title = this.activeServices.size === 1 ? `${[...this.activeServices][0]} Coverage` : 'Select 1 service filter';
      content = '<div style="font-size:10px;color:var(--text-dim)">Lighter = fewer, greener = more CROs</div>';
    } else {
      title = 'CRO Density';
      content = '<div style="font-size:10px;color:var(--text-dim)">Beige = no CROs, green = many CROs</div>';
    }

    el.innerHTML = `
      <div style="font-size:10px;color:var(--moss);margin-bottom:6px;font-weight:600">${title}</div>
      ${content}
    `;
    el.style.cssText = 'position:absolute;bottom:12px;left:12px;background:var(--surface);border:1px solid var(--border-soft);border-radius:var(--radius-sm);padding:10px 14px;min-width:140px;max-width:240px;z-index:10;box-shadow:var(--shadow-soft);font-size:11px';
  },
};
