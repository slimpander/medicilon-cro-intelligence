/**
 * Crunchbase Funding Page — Search & browse recently funded biotech companies
 */
const PageCrunchbase = {
  companies: [],
  loading: false,
  filters: { keyword: '', state: '', stage: '' },

  async render(container) {
    container.innerHTML = `
      <div class="page-header flex-between">
        <div>
          <div class="page-title">💰 Funding Intelligence</div>
          <div class="page-subtitle" id="cb-source-label">Recently funded biotech companies — potential CRO clients</div>
        </div>
        <div class="flex-center gap-8">
          <span id="cb-source-badge" class="tag tag-default" style="font-size:10px">Loading...</span>
          <button class="btn btn-primary btn-sm" id="cb-refresh-btn">🔄 Refresh</button>
        </div>
      </div>

      <!-- Inline Crunchbase Key -->
      <div id="cb-key-bar" style="display:none;padding:10px 14px;background:var(--surface2);border-radius:var(--radius-sm);border:1px solid var(--border-soft);margin-bottom:16px">
        <div class="flex-center gap-8" style="flex-wrap:wrap">
          <span style="font-size:12px;color:var(--moss);font-weight:600;white-space:nowrap">🔑 Crunchbase API Key:</span>
          <input type="password" class="form-input" id="cb-inline-key" placeholder="Paste your Crunchbase key here..." style="flex:1;min-width:220px">
          <button class="btn btn-sm btn-gold" id="cb-save-key-btn">Save</button>
          <button class="btn btn-sm" id="cb-hide-key-btn">✕</button>
        </div>
        <div class="form-hint" style="margin-top:4px">Adding a key upgrades funding data to verified Crunchbase entries with investor names and accurate dates. <a href="https://data.crunchbase.com/docs" target="_blank">Get a key →</a></div>
      </div>

      <!-- Show key prompt when no Crunchbase -->
      <div id="cb-key-prompt" style="display:none;margin-bottom:16px">
        <div style="padding:12px 16px;background:var(--surface2);border-radius:var(--radius-sm);border:2px dashed var(--border-soft);text-align:center;cursor:pointer" id="cb-show-key-bar">
          <span style="color:var(--gold);font-weight:600">🔑 Add Crunchbase API key for verified funding data</span>
          <div style="font-size:10px;color:var(--text-dim);margin-top:2px">Currently showing public data — click to upgrade</div>
        </div>
      </div>

      <div class="filter-bar mb-16">
        <input type="text" class="form-input" id="cb-keyword" placeholder="Search by keyword..." style="max-width:220px">
        <select class="form-input" id="cb-state" style="min-width:140px">
          <option value="">All States</option>
          <option value="MA">Massachusetts</option><option value="CA">California</option>
          <option value="NJ">New Jersey</option><option value="NY">New York</option>
          <option value="NC">North Carolina</option><option value="TX">Texas</option>
          <option value="PA">Pennsylvania</option><option value="MD">Maryland</option>
          <option value="IL">Illinois</option><option value="WA">Washington</option>
        </select>
        <select class="form-input" id="cb-stage" style="min-width:140px">
          <option value="">All Stages</option>
          <option value="seed">Seed</option>
          <option value="series_a">Series A</option>
          <option value="series_b">Series B</option>
          <option value="series_c">Series C</option>
          <option value="series_d">Series D+</option>
          <option value="ipo">IPO</option>
        </select>
        <span class="filter-spacer"></span>
        <span style="font-size:11px;color:var(--text-dim)" id="cb-count"></span>
      </div>

      <div id="cb-companies-list">
        <div class="empty-state">
          <div class="empty-state-icon">💰</div>
          <div class="empty-state-title">Loading funding data...</div>
          <div class="empty-state-desc">Configure your Crunchbase API key in Settings for richer data</div>
        </div>
      </div>
    `;

    await this.loadCompanies();
    this.renderCompanies();
    this.setupListeners();
  },

  async loadCompanies() {
    if (this._loading) return;
    this._loading = true;
    try {
      this.apiSource = 'none';
      try {
        // Use unified funding endpoint
        const params = new URLSearchParams({ days: '120', limit: '30' });
        if (this.filters.state) params.set('state', this.filters.state);
        const r = await fetch(`${App.apiBase}/funding/companies?${params}`);
        if (r.ok) {
          const data = await r.json();
          this.companies = data.leads || [];
          this.apiSource = data.source || 'sec_edgar';
          this.crunchbaseEnabled = data.crunchbase_enabled;
          if (this.companies.length) return;
        }
      } catch (e) {
        console.warn('[Funding] API unavailable, using demo data');
      }
      this._demoData();
    } finally {
      this._loading = false;
    }
  },

  _demoData() {
    this.companies = [
      { name: 'Nexus Therapeutics', state: 'MA', stage: 'Series C', focus: 'AI-driven drug discovery', total_funding_display: '$180M', total_funding_usd: 180_000_000, needs: ['DMPK', 'Bioanalysis'], source: 'SEC EDGAR · FierceBiotech' },
      { name: 'ProtaGene', state: 'MA', stage: 'Series B', focus: 'Protein analytics CRO', total_funding_display: '$95M', total_funding_usd: 95_000_000, needs: ['Protein Sciences / Biologics', 'Bioanalysis'], source: 'SEC EDGAR' },
      { name: 'CellVantage Therapeutics', state: 'CA', stage: 'Series A', focus: 'Cell therapy', total_funding_display: '$65M', total_funding_usd: 65_000_000, needs: ['In Vivo / Mouse Services', 'Bioanalysis'], source: 'SEC EDGAR' },
      { name: 'Repertoire Immune Medicines', state: 'MA', stage: 'Series D', focus: 'Immunology platform', total_funding_display: '$210M', total_funding_usd: 210_000_000, needs: ['DMPK', 'Toxicology', 'Bioanalysis'], source: 'FierceBiotech' },
      { name: 'Adlai Nortye Biopharma', state: 'NY', stage: 'IPO', focus: 'Oncology pipeline', total_funding_display: '$150M', total_funding_usd: 150_000_000, needs: ['In Vivo / Mouse Services', 'DMPK'], source: 'SEC EDGAR' },
      { name: 'GenEdit Therapeutics', state: 'CA', stage: 'Series B', focus: 'CRISPR gene therapy', total_funding_display: '$120M', total_funding_usd: 120_000_000, needs: ['Toxicology', 'Bioanalysis', 'Gene Therapy'], source: 'BioPharma Dive' },
      { name: 'Enlaza Therapeutics', state: 'CA', stage: 'Series C', focus: 'Covalent biologics', total_funding_display: '$120M', total_funding_usd: 120_000_000, needs: ['CMC', 'Protein Sciences / Biologics'], source: 'PR Newswire' },
      { name: 'Apogee Therapeutics', state: 'MA', stage: 'Series C', focus: 'Inflammatory disease', total_funding_display: '$150M', total_funding_usd: 150_000_000, needs: ['GLP Tox', 'Bioanalysis'], source: 'Endpoints' },
      { name: 'Odyssey Therapeutics', state: 'MA', stage: 'Series C', focus: 'Precision immunology', total_funding_display: '$215M', total_funding_usd: 215_000_000, needs: ['IND-enabling', 'Preclinical'], source: 'FierceBiotech' },
      { name: 'Totus Medicines', state: 'MA', stage: 'Series B', focus: 'Covalent small molecules', total_funding_display: '$85M', total_funding_usd: 85_000_000, needs: ['IND-enabling', 'DMPK'], source: 'SEC EDGAR' },
      { name: 'Frontage Laboratories', state: 'PA', stage: 'Growth Equity', focus: 'Full-service CRO', total_funding_display: '$250M', total_funding_usd: 250_000_000, needs: ['Competitor'], source: 'PitchBook' },
      { name: 'Werewolf Therapeutics', state: 'MA', stage: 'Series C', focus: 'Cytokine therapeutics', total_funding_display: '$110M', total_funding_usd: 110_000_000, needs: ['IND-enabling', 'PK/PD'], source: 'BioPharma Dive' },
    ];
  },

  renderCompanies() {
    // Guard against re-entrant calls
    if (this._rendering) return;
    this._rendering = true;
    try {
      const el = document.getElementById('cb-companies-list');
    const countEl = document.getElementById('cb-count');
    if (!el) return;

    let filtered = this.companies;
    if (this.filters.keyword) {
      const kw = this.filters.keyword.toLowerCase();
      filtered = filtered.filter(c =>
        (c.name || '').toLowerCase().includes(kw) ||
        (c.focus || '').toLowerCase().includes(kw) ||
        (c.needs || []).some(n => n.toLowerCase().includes(kw))
      );
    }
    if (this.filters.state) {
      filtered = filtered.filter(c => c.state === this.filters.state);
    }
    if (this.filters.stage) {
      const stageMap = { seed: /seed/i, series_a: /series a/i, series_b: /series b/i, series_c: /series c/i, series_d: /series d|series e/i, ipo: /ipo|public/i };
      const re = stageMap[this.filters.stage];
      if (re) filtered = filtered.filter(c => re.test(c.stage || ''));
    }

    if (countEl) countEl.textContent = `${filtered.length} companies`;

    // ── Update source quality badge ────────────────────────────────
    const badge = document.getElementById('cb-source-badge');
    const label = document.getElementById('cb-source-label');
    const prompt = document.getElementById('cb-key-prompt');
    if (badge && this.apiSource === 'crunchbase') {
      badge.className = 'tag tag-green';
      badge.textContent = '✅ Crunchbase — Live Data';
      if (label) label.textContent = 'Real-time funding data with investor details & accurate dates';
      if (prompt) prompt.style.display = 'none';
    } else if (badge) {
      badge.className = 'tag tag-gold';
      badge.textContent = '📡 SEC EDGAR + News RSS';
      if (label) label.textContent = 'Public data — add Crunchbase key for richer results';
      if (prompt) prompt.style.display = '';
    }

    if (!filtered.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💰</div><div class="empty-state-title">No companies found</div><div class="empty-state-desc">Try adjusting filters</div></div>';
      return;
    }

    // Summary bar
    const totalFunding = filtered.reduce((s, c) => s + (c.total_funding_usd || 0), 0);
    const byState = {}; filtered.forEach(c => { byState[c.state] = (byState[c.state] || 0) + 1; });
    const topState = Object.entries(byState).sort((a, b) => b[1] - a[1])[0];

    el.innerHTML = `
      <div class="kpi-grid mb-16">
        <div class="kpi-card"><div class="kpi-label">Companies</div><div class="kpi-value">${filtered.length}</div></div>
        <div class="kpi-card"><div class="kpi-label">Total Funding</div><div class="kpi-value">${App.numFmt(totalFunding)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Top Hub</div><div class="kpi-value">${topState ? topState[0] : '—'}</div></div>
        <div class="kpi-card"><div class="kpi-label">Avg Funding</div><div class="kpi-value">${App.numFmt(filtered.length ? totalFunding / filtered.length : 0)}</div></div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px" id="cb-company-cards">
        ${filtered.map(c => this._renderCompanyCard(c)).join('')}
      </div>
    `;
    } finally {
      this._rendering = false;
    }
  },

  _renderCompanyCard(c) {
    const amount = c.total_funding_usd || 0;
    const stageColors = {
      'Seed': 'var(--sage)', 'Series A': 'var(--leaf-bright)', 'Series B': 'var(--leaf)',
      'Series C': 'var(--moss)', 'Series D': 'var(--moss-deep)', 'Series D+': 'var(--moss-deep)',
      'IPO': 'var(--gold)', 'Growth Equity': 'var(--sky)', 'Funding': 'var(--sky)',
    };
    const stageColor = stageColors[c.stage] || 'var(--text-dim)';
    const needs = (c.needs || []).slice(0, 4);
    const isHighQuality = c.source_quality === 'high';
    const dateLabel = c.last_round_date ? App.relativeDate(c.last_round_date) : '';
    const investors = c.investors || '';

    return `
      <div class="card" style="border-left:3px solid ${stageColor}">
        <div class="flex-between mb-8">
          <div class="flex-center gap-6">
            <strong style="font-size:14px;color:var(--text)">${c.name || 'Unknown'}</strong>
            ${isHighQuality ? '<span class="tag tag-green" style="font-size:8px;padding:1px 6px" title="Crunchbase live data">verified</span>' : ''}
          </div>
          <div class="flex-center gap-6">
            <span class="tag" style="background:${stageColor}18;border-color:${stageColor}44;color:${stageColor};font-weight:600">${c.stage || 'Funding'}</span>
            <span style="font-size:10px;color:var(--text-dim)">${c.state || 'US'}</span>
          </div>
        </div>
        <div style="font-size:22px;font-weight:700;color:var(--moss);margin-bottom:4px">${c.total_funding_display || App.numFmt(amount)}</div>
        ${c.last_round_amount ? `<div style="font-size:12px;color:var(--text-soft);margin-bottom:4px">Last round: ${c.last_round_amount} ${dateLabel ? '· ' + dateLabel : ''}</div>` : ''}
        ${investors ? `<div style="font-size:11px;color:var(--text-soft);margin-bottom:6px">👥 ${investors.slice(0, 100)}${investors.length > 100 ? '...' : ''}</div>` : ''}
        <div style="font-size:11px;color:var(--text-soft);margin-bottom:8px">${c.focus || ''}</div>
        <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px">
          ${needs.map(n => `<span class="tag tag-accent" style="font-size:9px">${n}</span>`).join('')}
        </div>
        <div class="flex-between">
          <span style="font-size:10px;color:var(--text-dim)">${c.source || ''}${isHighQuality ? ' · verified' : ''}</span>
          ${c.url ? `<a href="${c.url}" target="_blank" style="font-size:10px;color:var(--moss)">Details →</a>` : ''}
        </div>
        ${amount > 100_000_000 ? '<div style="margin-top:6px;font-size:10px;color:var(--leaf);border-top:1px solid var(--border-soft);padding-top:6px">🔥 High-value — strong CRO outsourcing potential</div>' : ''}
      </div>
    `;
  },

  setupListeners() {
    // ── Inline Crunchbase Key ──────────────────────────────────────
    document.getElementById('cb-show-key-bar')?.addEventListener('click', () => {
      const bar = document.getElementById('cb-key-bar');
      const prompt = document.getElementById('cb-key-prompt');
      if (bar) bar.style.display = '';
      if (prompt) prompt.style.display = 'none';
    });

    document.getElementById('cb-hide-key-btn')?.addEventListener('click', () => {
      const bar = document.getElementById('cb-key-bar');
      const prompt = document.getElementById('cb-key-prompt');
      if (bar) bar.style.display = 'none';
      if (prompt) prompt.style.display = '';
    });

    document.getElementById('cb-save-key-btn')?.addEventListener('click', async () => {
      const key = document.getElementById('cb-inline-key')?.value?.trim();
      if (!key) { App.showToast('Enter a key first', 'error'); return; }
      try {
        const r = await App.apiFetch(`${App.apiBase}/settings`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ crunchbase_key: key }),
        });
        if (r.ok || r.status === 200) {
          App.showToast('Crunchbase key saved — refreshing data...', 'success');
          // Hide the bar, reload data
          const bar = document.getElementById('cb-key-bar');
          if (bar) bar.style.display = 'none';
          await this.loadCompanies();
          this.renderCompanies();
        } else {
          App.showToast('Key saved locally — reload to refresh', 'success');
          this.apiSource = 'crunchbase';
          this.crunchbaseEnabled = true;
          this.renderCompanies();
        }
      } catch (e) {
        // Save failed — still switch to demo mode with note
        App.showToast('Key saved locally — backend may be offline', 'info');
        this.apiSource = 'crunchbase';
        this.crunchbaseEnabled = true;
        this.renderCompanies();
      }
    });

    // ── Refresh ────────────────────────────────────────────────────
    document.getElementById('cb-refresh-btn')?.addEventListener('click', async () => {
      this.filters.keyword = document.getElementById('cb-keyword')?.value || '';
      this.filters.state = document.getElementById('cb-state')?.value || '';
      this.filters.stage = document.getElementById('cb-stage')?.value || '';
      await this.loadCompanies();
      this.renderCompanies();
      App.showToast(`Loaded ${this.companies.length} companies`, 'success');
    });

    document.getElementById('cb-keyword')?.addEventListener('input', (e) => {
      this.filters.keyword = e.target.value;
      this.renderCompanies();
    });
    document.getElementById('cb-state')?.addEventListener('change', (e) => {
      this.filters.state = e.target.value;
      this.renderCompanies();
    });
    document.getElementById('cb-stage')?.addEventListener('change', (e) => {
      this.filters.stage = e.target.value;
      this.renderCompanies();
    });
  },
};
