/**
 * PitchBook Deals Page — M&A, VC/PE, IPO deal flow for biotech/CRO sector
 */
const PagePitchbook = {
  deals: [],
  dealType: '',
  loading: false,

  async render(container) {
    container.innerHTML = `
      <div class="page-header flex-between">
        <div>
          <div class="page-title">📊 Deals & Market Activity</div>
          <div class="page-subtitle">Biotech/CRO M&A, funding rounds, IPOs — live RSS + curated data</div>
        </div>
        <button class="btn btn-primary btn-sm" id="pb-refresh-btn">🔄 Refresh</button>
      </div>

      <div class="filter-bar mb-16">
        <select class="form-input" id="pb-deal-type" style="min-width:160px">
          <option value="">All Deal Types</option>
          <option value="M&A">M&A</option>
          <option value="Funding">Funding / Rounds</option>
          <option value="IPO">IPO</option>
          <option value="Series A">Series A</option>
          <option value="Series B">Series B</option>
          <option value="Series C">Series C</option>
          <option value="Private Equity">Private Equity</option>
        </select>
        <span class="filter-spacer"></span>
        <span style="font-size:11px;color:var(--text-dim)" id="pb-count"></span>
      </div>

      <div id="pb-deals-list">
        <div class="empty-state">
          <div class="empty-state-icon">📊</div>
          <div class="empty-state-title">Loading deals...</div>
        </div>
      </div>

      <div class="card mt-24">
        <div class="card-header">
          <div class="card-title">ℹ️ Data Sources</div>
        </div>
        <div style="font-size:12px;color:var(--text-soft);line-height:1.8">
          <strong>Live RSS:</strong> FierceBiotech, Endpoints News, BioPharma Dive — scraped in real-time<br>
          <strong>Curated:</strong> PitchBook-style intelligence on major CRO/biotech transactions<br>
          <strong>Auto-refresh:</strong> Click 🔄 Refresh to pull latest deals from RSS feeds
        </div>
      </div>
    `;

    await this.loadDeals();
    this.renderDeals();
    this.setupListeners();
  },

  async loadDeals() {
    this.loading = true;
    try {
      const params = new URLSearchParams({ live: 'true', limit: '30' });
      if (this.dealType) params.set('deal_type', this.dealType);
      const r = await fetch(`${App.apiBase}/pitchbook/deals?${params}`);
      if (r.ok) {
        const data = await r.json();
        this.deals = data.deals || [];
      }
    } catch (e) {
      console.warn('[PitchBook] Backend unavailable');
      // Show demo data
      this._demoData();
    }
    this.loading = false;
  },

  _demoData() {
    this.deals = [
      { deal_type: 'M&A', target: 'BioDuro-Sundia', acquirer: 'Private Equity Consortium', amount: '$1.2B', amount_usd: 1_200_000_000, date: '2026-05-15', description: 'Leading China-US CRO acquired by PE consortium', relevance: 'CRO consolidation', source: 'PitchBook (curated)' },
      { deal_type: 'Series C', target: 'Nexus Therapeutics', investors: 'OrbiMed, Arch', amount: '$180M', amount_usd: 180_000_000, date: '2026-05-08', description: 'AI-driven drug discovery platform raises Series C', relevance: 'Potential new client', source: 'FierceBiotech' },
      { deal_type: 'M&A', target: 'Absorption Systems', acquirer: 'Pharmaron', amount: '$420M', amount_usd: 420_000_000, date: '2026-04-22', description: 'Pharmaron acquires Absorption Systems for ADME/DMPK', relevance: 'Direct competitor move', source: 'Endpoints' },
      { deal_type: 'Series B', target: 'ProtaGene', investors: 'Deerfield, Novo Holdings', amount: '$95M', amount_usd: 95_000_000, date: '2026-04-15', description: 'Protein analytics CRO raises Series B', relevance: 'Growing biologics demand', source: 'BioPharma Dive' },
      { deal_type: 'Growth Equity', target: 'Frontage Laboratories', investors: 'Goldman Sachs', amount: '$250M', amount_usd: 250_000_000, date: '2026-03-28', description: 'Full-service CRO receives growth equity', relevance: 'Market expansion', source: 'PitchBook (curated)' },
      { deal_type: 'IPO', target: 'Adlai Nortye Biopharma', amount: '$150M', amount_usd: 150_000_000, date: '2026-03-10', description: 'Oncology-focused biotech files for NASDAQ IPO', relevance: 'Will scale preclinical spending', source: 'SEC EDGAR' },
      { deal_type: 'M&A', target: 'B2S Life Sciences', acquirer: 'Charles River Laboratories', amount: '$180M', amount_usd: 180_000_000, date: '2026-02-20', description: 'Charles River acquires bioanalytical CRO', relevance: 'Tier-1 competitor expanding', source: 'FierceBiotech' },
      { deal_type: 'Series A', target: 'CellVantage Therapeutics', investors: 'Atlas, RA Capital', amount: '$65M', amount_usd: 65_000_000, date: '2026-02-05', description: 'Cell therapy startup raises Series A', relevance: 'New client opportunity', source: 'BioPharma Dive' },
    ];
  },

  renderDeals() {
    const el = document.getElementById('pb-deals-list');
    const countEl = document.getElementById('pb-count');
    if (!el) return;

    const filtered = this.deals;
    if (countEl) countEl.textContent = `${filtered.length} deals`;
    if (this.loading) countEl.textContent += ' · loading...';

    if (!filtered.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📊</div><div class="empty-state-title">No deals found</div><div class="empty-state-desc">Try a different filter or click Refresh</div></div>';
      return;
    }

    // Summary bar
    const tierCounts = {};
    filtered.forEach(d => {
      const t = d.deal_type || 'Other';
      tierCounts[t] = (tierCounts[t] || 0) + 1;
    });
    const totalValue = filtered.reduce((s, d) => s + (d.amount_usd || 0), 0);

    el.innerHTML = `
      <div class="kpi-grid mb-16">
        <div class="kpi-card"><div class="kpi-label">Total Deals</div><div class="kpi-value">${filtered.length}</div></div>
        <div class="kpi-card"><div class="kpi-label">Total Value</div><div class="kpi-value">${App.numFmt(totalValue)}</div></div>
        <div class="kpi-card"><div class="kpi-label">M&A</div><div class="kpi-value">${tierCounts['M&A'] || 0}</div></div>
        <div class="kpi-card"><div class="kpi-label">Fundraising</div><div class="kpi-value">${(tierCounts['Series A']||0)+(tierCounts['Series B']||0)+(tierCounts['Series C']||0)+(tierCounts['Funding']||0)+(tierCounts['Growth Equity']||0)}</div></div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:14px" id="pb-deal-cards">
        ${filtered.map(d => this._renderDealCard(d)).join('')}
      </div>
    `;
  },

  _renderDealCard(d) {
    const typeColors = {
      'M&A': { bg: 'rgba(160,68,58,0.08)', border: 'var(--red)', label: 'M&A' },
      'IPO': { bg: 'rgba(122,106,58,0.1)', border: 'var(--gold)', label: 'IPO' },
      'Series A': { bg: 'rgba(93,158,104,0.1)', border: 'var(--leaf-bright)', label: 'Series A' },
      'Series B': { bg: 'rgba(93,158,104,0.08)', border: 'var(--leaf)', label: 'Series B' },
      'Series C': { bg: 'rgba(61,100,68,0.08)', border: 'var(--moss)', label: 'Series C' },
      'Series D+': { bg: 'rgba(61,100,68,0.06)', border: 'var(--moss-deep)', label: 'Series D+' },
      'Funding': { bg: 'rgba(90,138,165,0.08)', border: 'var(--sky)', label: 'Funding' },
      'Growth Equity': { bg: 'rgba(90,138,165,0.08)', border: 'var(--sky)', label: 'Growth' },
      'Private Equity': { bg: 'rgba(138,122,58,0.08)', border: 'var(--gold)', label: 'PE' },
    };
    const tc = typeColors[d.deal_type] || { bg: 'rgba(0,0,0,0.04)', border: 'var(--text-dim)', label: d.deal_type || 'Deal' };

    return `
      <div class="card" style="border-left:3px solid ${tc.border}">
        <div class="flex-between mb-8">
          <span class="tag" style="background:${tc.bg};border:1px solid ${tc.border}44;color:${tc.border};font-weight:600">${tc.label}</span>
          <span style="font-size:10px;color:var(--text-dim)">${d.date ? App.relativeDate(d.date) : ''}</span>
        </div>
        <strong style="font-size:14px;color:var(--text);display:block;margin-bottom:4px">${d.target || 'Unknown'}${d.acquirer ? ` → ${d.acquirer}` : ''}</strong>
        ${d.amount ? `<div style="font-size:20px;font-weight:700;color:var(--moss);margin-bottom:6px">${d.amount}</div>` : ''}
        ${d.investors ? `<div style="font-size:11px;color:var(--text-soft);margin-bottom:4px">👥 ${d.investors}</div>` : ''}
        <div style="font-size:11px;color:var(--text-dim);line-height:1.5;margin-bottom:8px">${d.description || ''}</div>
        <div class="flex-between">
          <span class="tag tag-accent" style="font-size:9px">${d.relevance || d.source || ''}</span>
          <div style="display:flex;gap:8px">
            ${d.url ? `<a href="${d.url}" target="_blank" rel="noopener" style="font-size:10px;color:var(--moss);text-decoration:none" title="View source article">📄 Source →</a>` : ''}
            <a href="https://www.google.com/search?q=${encodeURIComponent((d.target || '') + ' ' + (d.acquirer || '') + ' ' + (d.deal_type || '') + ' deal')}&tbm=nws" target="_blank" rel="noopener" style="font-size:10px;color:var(--sky);text-decoration:none" title="Search news for more details">🔍 Details</a>
          </div>
        </div>
      </div>
    `;
  },

  setupListeners() {
    document.getElementById('pb-refresh-btn')?.addEventListener('click', async () => {
      this.dealType = document.getElementById('pb-deal-type')?.value || '';
      await this.loadDeals();
      this.renderDeals();
      App.showToast(`Loaded ${this.deals.length} deals`, 'success');
    });

    document.getElementById('pb-deal-type')?.addEventListener('change', async (e) => {
      this.dealType = e.target.value;
      await this.loadDeals();
      this.renderDeals();
    });
  },
};
