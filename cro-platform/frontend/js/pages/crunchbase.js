/**
 * SciLeads & Funding Intel Page — Dual-mode: SciLeads researcher search + funding companies
 * When SciLeads token is connected: primary view is researcher search
 * When not connected: shows public funding company data as fallback
 */
const PageCrunchbase = {
  companies: [],
  loading: false,
  viewMode: 'researchers',  // 'researchers' | 'funding'
  scileadsResults: [],
  scileadsTotal: 0,

  async render(container) {
    // Admin-only: redirect if not admin
    if (!App.isAdmin) {
      container.innerHTML = '<div class="empty-state" style="padding:60px"><div class="empty-state-icon">🔒</div><div class="empty-state-title">Admin Access Required</div><div class="empty-state-desc">SciLeads research tools are restricted to admin users.</div></div>';
      return;
    }
    // Check SciLeads token status
    this._checkToken();

    container.innerHTML = `
      <div class="page-header flex-between">
        <div>
          <div class="page-title">🔬 SciLeads & Funding Intel</div>
          <div class="page-subtitle" id="cb-source-label">Researcher discovery & funding intelligence</div>
        </div>
        <div class="flex-center gap-8">
          <span id="cb-source-badge" class="tag" style="font-size:10px">Checking...</span>
          <button class="btn btn-primary btn-sm" id="cb-refresh-btn">🔄 Refresh</button>
        </div>
      </div>

      <!-- View Mode Tabs -->
      <div id="cb-tab-bar" style="display:flex;gap:4px;margin-bottom:16px;border-bottom:2px solid var(--border-soft);padding-bottom:0">
        <button class="view-tab active" data-view="researchers" id="tab-researchers">
          🔬 Researcher Search
        </button>
        <button class="view-tab" data-view="leaderboard" id="tab-leaderboard">
          🏆 Priority Leaderboard
        </button>
        <button class="view-tab" data-view="funding" id="tab-funding">
          💰 Funding Companies
        </button>
        <span style="flex:1"></span>
        <span id="cb-tab-hint" style="font-size:10px;color:var(--text-dim);display:flex;align-items:center;margin-bottom:8px"></span>
      </div>

      <!-- SciLeads Not Connected Banner -->
      <div id="cb-sl-banner" style="display:none;margin-bottom:16px;padding:12px 16px;background:var(--surface2);border-radius:var(--radius-sm);border:2px dashed var(--border-soft)">
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
          <span style="font-size:24px">🔬</span>
          <div style="flex:1">
            <strong style="color:var(--gold)">SciLeads not connected</strong>
            <div style="font-size:11px;color:var(--text-dim)">Connect your token in Settings to unlock researcher search with email, H-index, publications, and clinical trial data</div>
          </div>
          <button class="btn btn-primary btn-sm" onclick="App.navigate('settings')">⚙️ Settings →</button>
        </div>
      </div>

      <!-- Priority Leaderboard View -->
      <div id="cb-leaderboard-view" style="display:none">
        <!-- Scoring Methodology (compact) -->
        <details style="margin-bottom:12px;background:var(--surface2);border-radius:8px;border:1px solid var(--border-soft);overflow:hidden">
          <summary style="padding:10px 14px;cursor:pointer;font-size:12px;font-weight:600;color:var(--moss);user-select:none">📊 How BD Priority Is Calculated (click to expand)</summary>
          <div style="padding:0 14px 14px;font-size:11px;color:var(--text-dim);line-height:1.8">
            <p style="margin:0 0 8px;color:var(--text-soft)">Each researcher is scored 0–100 based on <strong>6 dimensions</strong> weighted for CRO BD relevance:</p>
            <table style="width:100%;border-collapse:collapse;font-size:10px">
              <tr style="border-bottom:1px solid var(--border-dim)">
                <td style="padding:4px 8px;color:var(--accent);font-weight:600">Industry Affiliation</td>
                <td style="padding:4px 8px;text-align:right">+25 pts</td>
                <td style="padding:4px 8px;color:var(--text-dim)">Works at a pharma/biotech company (not academic)</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-dim)">
                <td style="padding:4px 8px;color:var(--green);font-weight:600">Verified Email</td>
                <td style="padding:4px 8px;text-align:right">+25 pts</td>
                <td style="padding:4px 8px;color:var(--text-dim)">SafeToSend — email verified and recent</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-dim)">
                <td style="padding:4px 8px;color:var(--gold);font-weight:600">Email Uncertain</td>
                <td style="padding:4px 8px;text-align:right">+10 pts</td>
                <td style="padding:4px 8px;color:var(--text-dim)">Email exists but not recently verified</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-dim)">
                <td style="padding:4px 8px;color:var(--purple);font-weight:600">H-Index ≥ 50</td>
                <td style="padding:4px 8px;text-align:right">+20 pts</td>
                <td style="padding:4px 8px;color:var(--text-dim)">High-impact researcher (top 5% in field)</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-dim)">
                <td style="padding:4px 8px;color:var(--purple);font-weight:600">H-Index ≥ 20</td>
                <td style="padding:4px 8px;text-align:right">+10 pts</td>
                <td style="padding:4px 8px;color:var(--text-dim)">Established researcher with moderate impact</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-dim)">
                <td style="padding:4px 8px;color:var(--sky);font-weight:600">Clinical Trials</td>
                <td style="padding:4px 8px;text-align:right">+15 pts</td>
                <td style="padding:4px 8px;color:var(--text-dim)">Actively running clinical trials — outsourcing signal</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-dim)">
                <td style="padding:4px 8px;color:var(--sky);font-weight:600">Publications ≥ 50</td>
                <td style="padding:4px 8px;text-align:right">+10 pts</td>
                <td style="padding:4px 8px;color:var(--text-dim)">Prolific researcher with sustained output</td>
              </tr>
              <tr>
                <td style="padding:4px 8px;color:var(--text-soft);font-weight:600">Funded Projects</td>
                <td style="padding:4px 8px;text-align:right">+5 pts</td>
                <td style="padding:4px 8px;color:var(--text-dim)">Has secured grant or venture funding</td>
              </tr>
            </table>
            <div style="margin-top:10px;padding:8px 10px;background:rgba(0,0,0,0.15);border-radius:6px">
              <strong style="color:var(--text)">Tier Classification:</strong>
              <span style="color:var(--green);margin-left:8px">S: 70–100</span> — Hot lead, contact immediately ·
              <span style="color:var(--accent);margin-left:8px">A: 50–69</span> — Strong lead, worth pursuing ·
              <span style="color:var(--gold);margin-left:8px">B: 35–49</span> — Monitor, potential ·
              <span style="color:var(--text-dim);margin-left:8px">C: 0–34</span> — Low priority
            </div>
          </div>
        </details>

        <!-- Leaderboard search -->
        <div class="filter-bar mb-16">
          <input type="text" class="form-input" id="cb-lb-search" placeholder="Search keyword to rank... (e.g., oncology, Pfizer, PROTAC)" style="flex:1;font-size:14px;padding:10px 14px">
          <button class="btn btn-primary" id="cb-lb-search-btn">🏆 Rank by Priority</button>
          <button class="btn btn-sm" id="cb-lb-reset-btn">Reset</button>
        </div>
        <div style="display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap">
          <span style="font-size:10px;color:var(--text-dim);white-space:nowrap;padding:4px 0">Quick:</span>
          <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickLeaderboard('oncology')">oncology</span>
          <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickLeaderboard('Pfizer')">Pfizer</span>
          <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickLeaderboard('DMPK')">DMPK</span>
          <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickLeaderboard('Alzheimer')">Alzheimer</span>
          <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickLeaderboard('ADC')">ADC</span>
          <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickLeaderboard('gene therapy')">gene therapy</span>
        </div>
        <div id="cb-lb-results">
          <div class="empty-state" style="padding:40px">
            <div class="empty-state-icon">🏆</div>
            <div class="empty-state-title">Priority Leaderboard</div>
            <div class="empty-state-desc">Enter a keyword above to rank all matching researchers by BD priority score</div>
          </div>
        </div>
      </div>

      <!-- Researcher Search View -->
      <div id="cb-researcher-view" style="display:flex;gap:0;position:relative">
        <!-- Main results area (shrinks when detail panel opens) -->
        <div id="cb-results-main" style="flex:1;min-width:0;transition:all 0.3s">
          <div class="filter-bar mb-16">
            <input type="text" class="form-input" id="cb-sl-search" placeholder="Search: company name (Pfizer), drug (Keytruda), disease (oncology), researcher (Jane Smith)..." style="flex:1;font-size:14px;padding:10px 14px">
            <select class="form-input" id="cb-sl-category" style="min-width:160px">
              <option value="">All Categories</option>
              <option value="Publications,ClinicalTrials,Funding,Tradeshows,Profile">All Data Sources</option>
              <option value="Publications">📄 Publications</option>
              <option value="ClinicalTrials">🧪 Clinical Trials</option>
              <option value="Funding">💰 Funding</option>
              <option value="Tradeshows">🎤 Tradeshows</option>
              <option value="Profile">👤 Profiles</option>
            </select>
            <button class="btn btn-primary" id="cb-sl-search-btn">🔍 Search</button>
          </div>
          <div style="display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap">
            <span style="font-size:10px;color:var(--text-dim);white-space:nowrap;padding:4px 0">Quick:</span>
            <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickSearch('oncology')">oncology</span>
            <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickSearch('Pfizer')">Pfizer</span>
            <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickSearch('BMS')">BMS</span>
            <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickSearch('Roche')">Roche</span>
            <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickSearch('DMPK')">DMPK</span>
            <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickSearch('Alzheimer')">Alzheimer</span>
            <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickSearch('PROTAC')">PROTAC</span>
            <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickSearch('ADC')">ADC</span>
            <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickSearch('gene therapy')">gene therapy</span>
            <span class="tag tag-default" style="cursor:pointer;font-size:10px" onclick="PageCrunchbase._quickSearch('cell therapy')">cell therapy</span>
          </div>
          <div id="cb-sl-results">
            <div class="empty-state" style="padding:40px">
              <div class="empty-state-icon">🔬</div>
              <div class="empty-state-title">Search SciLeads Researchers</div>
              <div class="empty-state-desc">Enter a company, drug, disease, or keyword above — then click Search</div>
            </div>
          </div>
          <div id="cb-sl-pagination" style="text-align:center;margin-top:16px;display:none"></div>
        </div>

        <!-- Side Detail Panel (slides in when a researcher is selected) -->
        <div id="cb-detail-panel" style="display:none;width:420px;min-width:420px;margin-left:16px;position:sticky;top:80px;align-self:flex-start;background:var(--surface);border:1px solid var(--border-soft);border-radius:10px;overflow:hidden;max-height:calc(100vh - 120px);overflow-y:auto;box-shadow:-4px 0 20px rgba(0,0,0,0.15)">
          <div style="padding:12px 16px;background:var(--surface2);display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border-soft)">
            <strong style="font-size:12px;color:var(--moss)">📋 BD Intelligence Report</strong>
            <button style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:16px;line-height:1" onclick="PageCrunchbase._closeDetail()">✕</button>
          </div>
          <div id="cb-detail-content" style="padding:16px"></div>
        </div>
      </div>

      <!-- Funding Companies View -->
      <div id="cb-funding-view" style="display:none">
        <div class="filter-bar mb-16">
          <input type="text" class="form-input" id="cb-keyword" placeholder="Filter by name or focus..." style="max-width:220px">
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
          </div>
        </div>
      </div>
    `;

    // Load data based on view mode
    await this.loadCompanies();
    this.renderCompanies();
    this.setupListeners();
    this._updateStatusBadge();
    this._updateBanner();

    // Enter key for search
    document.getElementById('cb-sl-search')?.addEventListener('keydown', e => {
      if (e.key === 'Enter') this._doSciLeadsSearch();
    });
  },

  _checkToken() {
    if (!this._tokenChecked) {
      this._tokenChecked = true;
      // Try refreshing from backend
      if (App.user) {
        App.apiFetch(`${App.apiBase}/settings`).then(r => r.json()).then(s => {
          App.settings = s;
          this._updateStatusBadge();
          this._updateBanner();
        }).catch(() => {});
      }
    }
  },

  _hasToken() {
    return !!(App.settings?.scilead_token || localStorage.getItem('scilead_token'));
  },

  _updateStatusBadge() {
    const badge = document.getElementById('cb-source-badge');
    const label = document.getElementById('cb-source-label');
    const hint = document.getElementById('cb-tab-hint');
    if (!badge) return;

    if (this._hasToken()) {
      badge.className = 'tag tag-green';
      badge.textContent = '✅ SciLeads Connected';
      if (label) label.textContent = 'Live researcher data with emails, H-index, publications, and clinical trials';
      if (hint) hint.textContent = 'Searching SciLeads researcher database';
    } else {
      badge.className = 'tag tag-gold';
      badge.textContent = '⬜ SciLeads — Not Connected';
      if (label) label.textContent = 'Funding intelligence from SEC EDGAR and public records';
      if (hint) hint.textContent = 'Connect in Settings for researcher search';
    }
  },

  _updateBanner() {
    const banner = document.getElementById('cb-sl-banner');
    if (!banner) return;
    banner.style.display = this._hasToken() ? 'none' : '';
  },

  _quickSearch(term) {
    const input = document.getElementById('cb-sl-search');
    if (input) {
      input.value = term;
      this._doSciLeadsSearch();
    }
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // SCILEADS RESEARCHER SEARCH
  // ═══════════════════════════════════════════════════════════════════════════

  async _doSciLeadsSearch(pageOffset = 0) {
    const input = document.getElementById('cb-sl-search');
    const resultsEl = document.getElementById('cb-sl-results');
    const paginationEl = document.getElementById('cb-sl-pagination');
    const keyword = input?.value?.trim();

    if (!keyword) {
      App.showToast('Enter a search term', 'error');
      return;
    }

    if (!this._hasToken()) {
      App.showToast('Connect SciLeads token in Settings first', 'error');
      return;
    }

    resultsEl.innerHTML = '<div class="empty-state" style="padding:30px"><div class="loader-spinner"></div><div class="empty-state-desc">Searching SciLeads...</div></div>';
    paginationEl.style.display = 'none';

    const category = document.getElementById('cb-sl-category')?.value || '';
    const sort = document.getElementById('cb-sl-sort')?.value || 'TotalMatches';

    try {
      const params = new URLSearchParams({
        keyword, count: '15', from_offset: String(pageOffset * 15)
      });
      if (category) params.set('categories', category);
      if (sort) params.set('order', sort);

      const r = await App.apiFetch(`${App.apiBase}/scilead/search?${params}`);
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        const detail = err.detail || '';
        // Check if it's a platform session expiry, not SciLeads
        if (r.status === 401 && detail.includes('Not authenticated')) {
          resultsEl.innerHTML = `<div class="empty-state" style="padding:40px">
            <div class="empty-state-icon">🔐</div>
            <div class="empty-state-title">Platform Session Expired</div>
            <div class="empty-state-desc">Your Medicilon platform login has expired. SciLeads token is still valid.</div>
            <button class="btn btn-primary mt-8" onclick="document.getElementById('login-modal-overlay').style.display='flex'">🔑 Log In Again →</button>
          </div>`;
        } else {
          resultsEl.innerHTML = `<div class="empty-state" style="padding:40px">
            <div class="empty-state-icon">⚠️</div>
            <div class="empty-state-title">${detail || 'Search failed'}</div>
            <div class="empty-state-desc">${r.status === 401 ? 'SciLeads token may have expired — refresh in Settings' : 'Backend error — try again'}</div>
            ${r.status === 401 ? '<button class="btn btn-sm mt-8" onclick="App.navigate(\'settings\')">⚙️ Settings →</button>' : ''}
          </div>`;
        }
        return;
      }

      const data = await r.json();
      this.scileadsResults = data.researchers || [];
      this.scileadsTotal = data.total_results || 0;
      this._currentPage = pageOffset;

      if (!this.scileadsResults.length) {
        resultsEl.innerHTML = `<div class="empty-state" style="padding:40px">
          <div class="empty-state-icon">🔍</div>
          <div class="empty-state-title">No researchers found</div>
          <div class="empty-state-desc">Try a different search term or broader category filter</div>
        </div>`;
        return;
      }

      // Stats bar
      const safeEmails = this.scileadsResults.filter(r => r.email_quality === 'SafeToSend').length;
      const industryCount = this.scileadsResults.filter(r => r.company_type?.includes('Industry')).length;
      const avgH = this.scileadsResults.reduce((s, r) => s + (r.h_index_3yr || 0), 0) / this.scileadsResults.length;

      resultsEl.innerHTML = `
        <div class="kpi-grid mb-16">
          <div class="kpi-card"><div class="kpi-label">Total Results</div><div class="kpi-value">${this.scileadsTotal.toLocaleString()}</div></div>
          <div class="kpi-card"><div class="kpi-label">This Page</div><div class="kpi-value">${this.scileadsResults.length}</div></div>
          <div class="kpi-card"><div class="kpi-label" style="color:var(--green)">With Email</div><div class="kpi-value">${safeEmails}</div></div>
          <div class="kpi-card"><div class="kpi-label">Avg H-Index</div><div class="kpi-value">${avgH.toFixed(0)}</div></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:12px">
          ${this.scileadsResults.map(r => this._renderResearcherCard(r)).join('')}
        </div>
      `;

      // Pagination
      const totalPages = Math.ceil(Math.min(this.scileadsTotal, 150) / 15);
      if (totalPages > 1) {
        paginationEl.style.display = '';
        paginationEl.innerHTML = `
          <button class="btn btn-sm" onclick="PageCrunchbase._doSciLeadsSearch(${pageOffset - 1})" ${pageOffset === 0 ? 'disabled' : ''}>← Previous</button>
          <span style="margin:0 12px;font-size:12px;color:var(--text-dim)">Page ${pageOffset + 1} of ${totalPages}</span>
          <button class="btn btn-sm" onclick="PageCrunchbase._doSciLeadsSearch(${pageOffset + 1})" ${pageOffset >= totalPages - 1 ? 'disabled' : ''}>Next →</button>
        `;
      }

    } catch (e) {
      resultsEl.innerHTML = `<div class="empty-state" style="padding:40px">
        <div class="empty-state-icon">❌</div>
        <div class="empty-state-title">Search failed</div>
        <div class="empty-state-desc">${e.message || 'Backend may be offline'}</div>
      </div>`;
    }
  },

  _renderResearcherCard(r) {
    const hasEmail = r.email_quality === 'SafeToSend';
    const isIndustry = (r.company_type || '').includes('Industry');
    const hasTrials = r.total_clinical_trials > 0;
    const hasPosters = r.recent_posters?.length > 0;
    const researcherIndex = this.scileadsResults.indexOf(r);

    // Category tags
    const tags = [];
    if (hasEmail) tags.push('<span class="tag tag-green" style="font-size:8px;padding:1px 5px">📧 Email Verified</span>');
    else if (r.email_quality) tags.push('<span class="tag tag-gold" style="font-size:8px;padding:1px 5px">⚠️ Email Uncertain</span>');
    if (isIndustry) tags.push('<span class="tag tag-accent" style="font-size:8px;padding:1px 5px">🏢 Industry</span>');
    if (hasTrials) tags.push('<span class="tag" style="font-size:8px;padding:1px 5px;background:rgba(46,204,113,0.1);border-color:rgba(46,204,113,0.3);color:var(--green)">🧪 Clinical Trials</span>');
    if (hasPosters) tags.push('<span class="tag" style="font-size:8px;padding:1px 5px;background:rgba(0,180,255,0.1);border-color:rgba(0,180,255,0.3);color:var(--sky)">🎤 Tradeshow</span>');

    // Signal highlights
    const signals = [];
    if (r.total_publications) signals.push(`📄 ${r.total_publications} pubs`);
    if (r.total_clinical_trials) signals.push(`🧪 ${r.total_clinical_trials} trials`);
    if (r.total_tradeshows) signals.push(`🎤 ${r.total_tradeshows} shows`);
    if (r.h_index_3yr >= 20) signals.push(`⭐ H-index ${r.h_index_3yr}`);

    // Recent publication highlight
    const recentPub = r.recent_publications?.[0];
    const pubPreview = recentPub ? `<span style="font-size:10px;color:var(--text-dim);line-height:1.3">📝 ${recentPub.title?.slice(0, 100)}${(recentPub.title?.length || 0) > 100 ? '...' : ''}</span>` : '';

    return `
      <div class="card" style="border-left:3px solid ${hasEmail ? 'var(--green)' : isIndustry ? 'var(--accent)' : 'var(--gold)'};cursor:pointer;transition:transform 0.15s"
           onclick="PageCrunchbase._openDetail(${researcherIndex})"
           onmouseover="this.style.transform='translateX(2px)'" onmouseout="this.style.transform=''">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
          <div style="flex:1;min-width:0">
            <strong style="font-size:13px;color:var(--text);line-height:1.3">${r.name || 'Unknown'}</strong>
            <div style="font-size:11px;color:var(--accent);margin-top:2px">${r.title || ''}</div>
          </div>
          ${r.h_index_3yr ? `<span style="font-size:18px;font-weight:700;color:var(--purple);white-space:nowrap;margin-left:8px">H${r.h_index_3yr}</span>` : ''}
        </div>

        <div style="font-size:10px;color:var(--text-soft);margin-bottom:4px">${r.company || ''}${r.country ? ' · ' + r.country : ''}</div>

        ${r.email ? `<div style="font-size:11px;color:var(--moss);margin-bottom:4px;word-break:break-all">${r.email}</div>` : ''}

        ${signals.length ? `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px;font-size:10px;color:var(--text-dim)">${signals.map(s => `<span>${s}</span>`).join('')}</div>` : ''}

        ${pubPreview ? `<div style="margin-bottom:6px">${pubPreview}</div>` : ''}

        <div style="display:flex;flex-wrap:wrap;gap:3px;margin-bottom:4px">${tags.join('')}</div>

        ${r.top_mesh?.length ? `<div style="margin-top:6px;font-size:9px;color:var(--text-dim);border-top:1px solid var(--border-dim);padding-top:6px">🔬 ${r.top_mesh.slice(0, 4).map(m => m.replace(/#\\d+$/, '')).join(' · ')}</div>` : ''}
      </div>
    `;
  },

  // ── BD Scoring Engine (shared) ─────────────────────────────────────────
  _scoreResearcher(r) {
    const isIndustry = (r.company_type || '').includes('Industry');
    const hasEmail = r.email_quality === 'SafeToSend';
    const hasUncertainEmail = r.email_quality === 'Uncertain';
    const hasTrials = r.total_clinical_trials > 0;

    let score = 0;
    if (isIndustry) score += 25;
    if (hasEmail) score += 25;
    else if (hasUncertainEmail) score += 10;
    if (r.h_index_3yr >= 50) score += 20;
    else if (r.h_index_3yr >= 20) score += 10;
    if (hasTrials) score += 15;
    if (r.total_publications >= 50) score += 10;
    if (r.total_funding_projects > 0) score += 5;

    const tier = score >= 70 ? 'S' : score >= 50 ? 'A' : score >= 35 ? 'B' : 'C';
    return { score, tier };
  },

  // ── Priority Leaderboard ────────────────────────────────────────────────
  _quickLeaderboard(term) {
    const input = document.getElementById('cb-lb-search');
    if (input) {
      input.value = term;
      this._doLeaderboard();
    }
  },

  async _doLeaderboard() {
    const input = document.getElementById('cb-lb-search');
    const resultsEl = document.getElementById('cb-lb-results');
    const keyword = input?.value?.trim();

    if (!keyword) { App.showToast('Enter a keyword to rank', 'error'); return; }
    if (!this._hasToken()) { App.showToast('Connect SciLeads token in Settings', 'error'); return; }

    resultsEl.innerHTML = '<div class="empty-state" style="padding:30px"><div class="loader-spinner"></div><div class="empty-state-desc">Fetching & ranking researchers...</div></div>';

    try {
      // Fetch up to 50 results and re-rank by BD score (throttled for rate-limit safety)
      const params = new URLSearchParams({ keyword, count: '50' });
      const r = await App.apiFetch(`${App.apiBase}/scilead/search?${params}`);
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        const detail = err.detail || '';
        if (r.status === 401 && detail.includes('Not authenticated')) {
          resultsEl.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🔐</div><div class="empty-state-title">Platform Session Expired</div><div class="empty-state-desc">Your Medicilon login has expired. Click the 👤 icon to log in again.</div><button class="btn btn-primary mt-8" onclick="document.getElementById('login-modal-overlay').style.display='flex'">🔑 Log In →</button></div>`;
        } else {
          resultsEl.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-title">${detail || 'Search failed'}</div><div class="empty-state-desc">${r.status === 401 ? 'SciLeads token may have expired — refresh in Settings' : ''}</div></div>`;
        }
        return;
      }

      const data = await r.json();
      let researchers = data.researchers || [];
      const totalAvailable = data.total_results || 0;

      if (!researchers.length) {
        resultsEl.innerHTML = `
          <div class="kpi-grid mb-16">
            <div class="kpi-card"><div class="kpi-label">Total Matched</div><div class="kpi-value">0</div></div>
            <div class="kpi-card"><div class="kpi-label" style="color:var(--green)">S Tier (70+)</div><div class="kpi-value" style="color:var(--green)">0</div></div>
            <div class="kpi-card"><div class="kpi-label" style="color:var(--accent)">A Tier (50–69)</div><div class="kpi-value" style="color:var(--accent)">0</div></div>
            <div class="kpi-card"><div class="kpi-label" style="color:var(--gold)">B Tier (35–49)</div><div class="kpi-value" style="color:var(--gold)">0</div></div>
          </div>
          <div class="empty-state" style="padding:30px">
            <div class="empty-state-icon">🔍</div>
            <div class="empty-state-title">No researchers found for "${keyword}"</div>
            <div class="empty-state-desc">Try a broader keyword (company name, drug, disease area) or check that your SciLeads token is valid</div>
          </div>
        `;
        return;
      }

      // Score every researcher
      const scored = researchers.map(r => ({ ...r, _bdScore: this._scoreResearcher(r) }));
      scored.sort((a, b) => b._bdScore.score - a._bdScore.score);

      // Tally by tier
      const tierCount = { S: 0, A: 0, B: 0, C: 0 };
      scored.forEach(r => tierCount[r._bdScore.tier]++);

      // Build results
      resultsEl.innerHTML = `
        <div class="kpi-grid mb-16">
          <div class="kpi-card">
            <div class="kpi-label">Total Matched</div>
            <div class="kpi-value">${totalAvailable.toLocaleString()}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label" style="color:var(--green)">S Tier (70+)</div>
            <div class="kpi-value" style="color:var(--green)">${tierCount.S}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label" style="color:var(--accent)">A Tier (50–69)</div>
            <div class="kpi-value" style="color:var(--accent)">${tierCount.A}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label" style="color:var(--gold)">B Tier (35–49)</div>
            <div class="kpi-value" style="color:var(--gold)">${tierCount.B}</div>
          </div>
        </div>

        ${scored.length ? `
          <div style="font-size:11px;color:var(--text-dim);margin-bottom:12px;padding-left:8px;border-left:3px solid var(--border-soft)">
            🔍 Keyword: <strong style="color:var(--accent)">${keyword}</strong> · Showing <strong>${scored.length}</strong> of ${totalAvailable.toLocaleString()} results · Ranked by BD Priority
          </div>
        ` : ''}

        <div style="display:flex;flex-direction:column;gap:8px">
          ${scored.slice(0, 30).map((r, i) => this._renderLeaderboardRow(r, i)).join('')}
        </div>

        ${scored.length > 30 ? `<div style="text-align:center;padding:12px;font-size:10px;color:var(--text-dim)">Showing top 30 of ${scored.length} ranked researchers</div>` : ''}
      `;

    } catch (e) {
      resultsEl.innerHTML = `<div class="empty-state"><div class="empty-state-icon">❌</div><div class="empty-state-title">Search failed</div><div class="empty-state-desc">${e.message || ''}</div></div>`;
    }
  },

  _renderLeaderboardRow(r, index) {
    const s = r._bdScore;
    const tierColors = { S: 'var(--green)', A: 'var(--accent)', B: 'var(--gold)', C: 'var(--text-dim)' };
    const tierBg = { S: 'rgba(46,204,113,0.08)', A: 'rgba(0,180,255,0.08)', B: 'rgba(255,200,0,0.08)', C: 'transparent' };
    const rankIcon = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}`;

    const signals = [];
    if (r.company_type?.includes('Industry')) signals.push('🏢 Industry');
    if (r.email_quality === 'SafeToSend') signals.push('📧 Verified');
    if (r.total_clinical_trials) signals.push(`🧪 ${r.total_clinical_trials} trials`);
    if (r.h_index_3yr >= 20) signals.push(`⭐ H${r.h_index_3yr}`);

    return `
      <div style="display:flex;align-items:center;gap:12px;padding:10px 14px;background:${tierBg[s.tier]};border-radius:8px;border-left:4px solid ${tierColors[s.tier]};cursor:pointer"
           onclick="PageCrunchbase._showLeaderboardDetail(this)"
           data-researcher='${JSON.stringify(r).replace(/'/g, "&#39;").replace(/"/g, '&quot;')}'>
        <div style="font-size:18px;font-weight:700;color:${tierColors[s.tier]};min-width:32px;text-align:center">${rankIcon}</div>
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;gap:8px">
            <strong style="font-size:12px;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${r.name || 'Unknown'}</strong>
            <span class="tag" style="font-size:8px;font-weight:700;background:${tierColors[s.tier]};color:#fff;padding:1px 5px;border-radius:3px;border:none">${s.tier} · ${s.score}</span>
          </div>
          <div style="font-size:10px;color:var(--text-soft);margin-top:2px">${r.title || ''} · ${r.company || ''}${r.country ? ' · ' + r.country : ''}</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px">${signals.map(sig => `<span style="font-size:9px;color:var(--text-dim)">${sig}</span>`).join('')}</div>
        </div>
        ${r.email ? `<div style="font-size:9px;color:var(--moss);max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${r.email}">✉️ ${r.email}</div>` : ''}
      </div>
    `;
  },

  _showLeaderboardDetail(el) {
    // Expand/collapse the row to show a mini detail
    const existing = el.nextElementSibling;
    if (existing?.classList.contains('lb-detail')) {
      existing.remove();
      return;
    }
    // Remove any other open details
    document.querySelectorAll('.lb-detail').forEach(d => d.remove());

    const r = JSON.parse(el.getAttribute('data-researcher') || '{}');
    const s = r._bdScore;
    const tierColors = { S: 'var(--green)', A: 'var(--accent)', B: 'var(--gold)', C: 'var(--text-dim)' };
    const pubCount = r.recent_publications?.length || 0;
    const trialCount = r.clinical_trials?.length || 0;

    const detail = document.createElement('div');
    detail.className = 'lb-detail';
    detail.style.cssText = 'padding:10px 14px 10px 48px;font-size:10px;color:var(--text-dim);line-height:1.6;border-bottom:1px solid var(--border-dim);background:var(--surface2)';
    detail.innerHTML = `
      <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:6px">
        <span>📄 ${r.total_publications || 0} pubs lifetime</span>
        <span>🧪 ${r.total_clinical_trials || 0} clinical trials</span>
        <span>💰 $${((r.total_funding_alltime || 0) / 1000).toFixed(0)}K funding</span>
        <span>👥 ${r.total_collaborators || 0} co-authors</span>
        <span>📊 SJR ${r.sjr_3yr || '—'}</span>
      </div>
      ${r.recent_publications?.[0] ? `<div style="font-size:10px;color:var(--text-soft)">📝 Latest: ${r.recent_publications[0].title?.slice(0, 120)}${(r.recent_publications[0].title?.length || 0) > 120 ? '...' : ''}</div>` : ''}
      ${r.email ? `<div style="margin-top:4px"><a href="mailto:${r.email}" style="font-size:10px;color:var(--moss)">📧 Send Email →</a>${r.linkedin ? ` &nbsp; <a href="https://${r.linkedin}" target="_blank" style="color:var(--sky)">🔗 LinkedIn</a>` : ''}</div>` : ''}
    `;
    el.after(detail);
  },

  // ── BD Intelligence Report (side panel) ────────────────────────────────
  _openDetail(index) {
    const r = this.scileadsResults[index];
    if (!r) return;

    const panel = document.getElementById('cb-detail-panel');
    const content = document.getElementById('cb-detail-content');
    if (!panel || !content) return;

    panel.style.display = '';
    const report = this._generateBDReport(r);
    content.innerHTML = report;

    // Highlight selected card
    const cards = document.querySelectorAll('#cb-sl-results .card');
    cards.forEach((c, i) => c.style.outline = i === index ? '2px solid var(--moss)' : 'none');
  },

  _closeDetail() {
    const panel = document.getElementById('cb-detail-panel');
    if (panel) panel.style.display = 'none';
    const cards = document.querySelectorAll('#cb-sl-results .card');
    cards.forEach(c => c.style.outline = 'none');
  },

  _generateBDReport(r) {
    const hasEmail = r.email_quality === 'SafeToSend';
    const isIndustry = (r.company_type || '').includes('Industry');
    const hasTrials = (r.total_clinical_trials || 0) > 0;

    // Use shared scoring engine
    const { score, tier } = this._scoreResearcher(r);
    const tierColor = { S: 'var(--green)', A: 'var(--accent)', B: 'var(--gold)', C: 'var(--text-dim)' };
    const name = r.name || 'Unknown Researcher';
    const firstName = name.split(' ')[0] || 'researcher';

    // Contact recommendation
    let contactRec = '';
    if (hasEmail && isIndustry && score >= 50) {
      contactRec = '✅ <strong style="color:var(--green)">HIGH PRIORITY</strong> — Verified email, industry decision-maker, active research. Contact immediately.';
    } else if (hasEmail && isIndustry) {
      contactRec = '📧 <strong style="color:var(--accent)">WORTH CONTACTING</strong> — Verified email, industry-affiliated. Qualify further before outreach.';
    } else if (hasEmail && score >= 40) {
      contactRec = '📧 <strong style="color:var(--gold)">ACADEMIC KOL</strong> — Contact for scientific advisory or collaboration.';
    } else if (r.email_quality === 'Uncertain') {
      contactRec = '⚠️ <strong style="color:var(--gold)">EMAIL UNCERTAIN</strong> — Verify email before outreach.';
    } else if (!r.email) {
      contactRec = '❌ <strong style="color:var(--text-dim)">NO EMAIL</strong> — Monitor activity only.';
    } else {
      contactRec = '📧 Contact available — evaluate context before outreach.';
    }

    // Recent publications
    const pubsHtml = (r.recent_publications || []).map(p => `
      <div style="margin-bottom:6px;padding-bottom:6px;border-bottom:1px solid var(--border-dim)">
        <div style="font-size:11px;line-height:1.4;color:var(--text)">📄 ${p.title || 'Untitled'}</div>
        <div style="font-size:9px;color:var(--text-dim);margin-top:2px">${p.journal || ''} · ${p.date || ''}${p.impact_factor ? ' · IF ' + p.impact_factor : ''}</div>
      </div>
    `).join('');

    // Clinical trials
    const trialsHtml = (r.clinical_trials || []).map(t => `
      <div style="margin-bottom:4px">
        <span class="tag" style="font-size:9px;background:rgba(46,204,113,0.1);border-color:rgba(46,204,113,0.2);color:var(--green)">${t.phase || 'N/A'}</span>
        <span style="font-size:10px;color:var(--text-dim)">${t.status || ''} · ${(t.title || '').slice(0, 60)}...</span>
      </div>
    `).join('');

    // BD services match
    const servicesMatch = [];
    const meshText = (r.top_mesh || []).join(' ').toLowerCase();
    if (meshText.match(/drug|pharmacokinetic|bioavail|metabolism|clearance/)) servicesMatch.push('DMPK');
    if (meshText.match(/toxicit|safety|adverse|carcinogen|mutagen/)) servicesMatch.push('Toxicology');
    if (meshText.match(/assay|chromatograph|mass spectrom|analytical|biomarker/)) servicesMatch.push('Bioanalysis');
    if (meshText.match(/formulation|excipient|stability|manufactur|cell line/)) servicesMatch.push('CMC');
    if (meshText.match(/mouse|mice|animal model|in vivo|rodent|xenograft/)) servicesMatch.push('In Vivo');
    if (meshText.match(/genomic|sequencing|crispr|gene|rna|dna/)) servicesMatch.push('Genomics');
    if (meshText.match(/antibody|protein|peptide|biologic/)) servicesMatch.push('Protein');

    return `
      <div style="margin-bottom:16px;text-align:center">
        <div style="font-size:40px;font-weight:700;color:${tierColor[tier]}">${tier}</div>
        <div style="font-size:10px;font-weight:600;color:${tierColor[tier]};text-transform:uppercase;letter-spacing:.1em">BD Priority · Score ${score}/100</div>
      </div>
      <div style="background:var(--surface2);padding:12px;border-radius:8px;margin-bottom:12px">
        <strong style="font-size:14px;color:var(--text)">${name}</strong>
        <div style="font-size:11px;color:var(--accent);margin-top:2px">${r.title || 'No title listed'}</div>
        <div style="font-size:11px;color:var(--text-soft);margin-top:2px">${r.company || ''}${r.country ? ' · ' + r.country : ''}</div>
        ${r.email ? `<div style="margin-top:6px;font-size:12px;font-family:monospace;color:var(--moss);word-break:break-all">✉️ ${r.email}</div>` : ''}
        ${r.email_quality ? `<div style="font-size:10px;color:${hasEmail ? 'var(--green)' : 'var(--gold)'};margin-top:2px">Email quality: ${r.email_quality}</div>` : ''}
        ${r.phone ? `<div style="font-size:11px;color:var(--text-dim);margin-top:2px">📞 ${r.phone}</div>` : ''}
        ${r.linkedin ? `<div style="margin-top:4px"><a href="https://${r.linkedin}" target="_blank" style="font-size:10px;color:var(--sky)">🔗 LinkedIn →</a></div>` : ''}
      </div>
      <div style="padding:10px 12px;background:${score >= 50 ? 'rgba(46,204,113,0.08)' : 'rgba(255,255,255,0.03)'};border-radius:6px;margin-bottom:12px;font-size:11px;line-height:1.5">${contactRec}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:12px">
        <div style="padding:8px;background:var(--surface2);border-radius:6px;text-align:center">
          <div style="font-size:16px;font-weight:700;color:var(--purple)">${r.h_index_3yr || '—'}</div>
          <div style="font-size:9px;color:var(--text-dim)">H-Index (3yr)</div>
        </div>
        <div style="padding:8px;background:var(--surface2);border-radius:6px;text-align:center">
          <div style="font-size:16px;font-weight:700;color:var(--accent)">${r.total_publications || 0}</div>
          <div style="font-size:9px;color:var(--text-dim)">Publications</div>
        </div>
        <div style="padding:8px;background:var(--surface2);border-radius:6px;text-align:center">
          <div style="font-size:16px;font-weight:700;color:var(--green)">${r.total_clinical_trials || 0}</div>
          <div style="font-size:9px;color:var(--text-dim)">Clinical Trials</div>
        </div>
        <div style="padding:8px;background:var(--surface2);border-radius:6px;text-align:center">
          <div style="font-size:16px;font-weight:700;color:var(--gold)">${r.total_funding_projects || 0}</div>
          <div style="font-size:9px;color:var(--text-dim)">Funded Projects</div>
        </div>
      </div>
      ${servicesMatch.length ? `
        <div style="margin-bottom:12px">
          <strong style="font-size:10px;color:var(--text-soft);text-transform:uppercase;letter-spacing:.05em">🎯 CRO Service Match</strong>
          <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px">${servicesMatch.map(s => `<span class="tag tag-accent" style="font-size:9px">${s}</span>`).join('')}</div>
        </div>
      ` : ''}
      ${pubsHtml ? `<div style="margin-bottom:12px"><strong style="font-size:10px;color:var(--text-soft);text-transform:uppercase;letter-spacing:.05em">📚 Recent Publications</strong><div style="margin-top:6px;max-height:160px;overflow-y:auto">${pubsHtml}</div></div>` : ''}
      ${trialsHtml ? `<div style="margin-bottom:12px"><strong style="font-size:10px;color:var(--text-soft);text-transform:uppercase;letter-spacing:.05em">🧪 Clinical Trials</strong><div style="margin-top:6px">${trialsHtml}</div></div>` : ''}
      ${r.top_mesh?.length ? `<div style="margin-bottom:12px"><strong style="font-size:10px;color:var(--text-soft);text-transform:uppercase;letter-spacing:.05em">🔬 Research Focus</strong><div style="margin-top:6px;font-size:10px;color:var(--text-dim);line-height:1.5">${r.top_mesh.map(m => `<span style="display:inline-block;background:var(--surface2);padding:2px 6px;border-radius:3px;margin:2px">${m.replace(/#\\d+$/, '')}</span>`).join('')}</div></div>` : ''}
      <div style="padding:10px 12px;background:var(--surface2);border-radius:6px;border-left:3px solid ${tierColor[tier]}">
        <strong style="font-size:10px;color:var(--text-soft);text-transform:uppercase;letter-spacing:.05em">📋 BD Recommendation</strong>
        <div style="font-size:10px;color:var(--text-dim);margin-top:4px;line-height:1.5">            ${isIndustry && hasEmail
            ? `Contact ${firstName} regarding Medicilon CRO services. ${hasTrials ? 'Active clinical programs indicate outsourcing potential.' : 'Engage for pipeline awareness.'}`
            : `Monitor ${firstName}'s activity for scientific advisory or collaboration opportunities. ${hasTrials ? 'Active clinical programs in area.' : ''}`
          }</div>
      </div>
    `;
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // FUNDING COMPANIES (existing logic, preserved)
  // ═══════════════════════════════════════════════════════════════════════════

  async loadCompanies() {
    if (this._loading) return;
    this._loading = true;
    try {
      this.apiSource = this._hasToken() ? 'scilead' : 'none';
      try {
        const params = new URLSearchParams({ days: '120', limit: '30' });
        if (this.filters?.state) params.set('state', this.filters.state);
        const r = await fetch(`${App.apiBase}/funding/companies?${params}`);
        if (r.ok) {
          const data = await r.json();
          this.companies = data.leads || [];
          this.apiSource = data.source || 'sec_edgar';
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
    if (this._rendering) return;
    this._rendering = true;
    try {
      const el = document.getElementById('cb-companies-list');
      const countEl = document.getElementById('cb-count');
      if (!el) return;

      let filtered = this.companies;
      if (this.filters?.keyword) {
        const kw = this.filters.keyword.toLowerCase();
        filtered = filtered.filter(c =>
          (c.name || '').toLowerCase().includes(kw) ||
          (c.focus || '').toLowerCase().includes(kw) ||
          (c.needs || []).some(n => n.toLowerCase().includes(kw))
        );
      }
      if (this.filters?.state) filtered = filtered.filter(c => c.state === this.filters.state);
      if (this.filters?.stage) {
        const stageMap = { seed: /seed/i, series_a: /series a/i, series_b: /series b/i, series_c: /series c/i, series_d: /series d|series e/i, ipo: /ipo|public/i };
        const re = stageMap[this.filters.stage];
        if (re) filtered = filtered.filter(c => re.test(c.stage || ''));
      }

      if (countEl) countEl.textContent = `${filtered.length} companies`;

      if (!filtered.length) {
        el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💰</div><div class="empty-state-title">No companies found</div><div class="empty-state-desc">Try adjusting filters</div></div>';
        return;
      }

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
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px">
          ${filtered.map(c => this._renderCompanyCard(c)).join('')}
        </div>
      `;
    } finally {
      this._rendering = false;
    }
  },

  _renderCompanyCard(c) {
    const amount = c.total_funding_usd || 0;
    const stageColors = { 'Seed': 'var(--sage)', 'Series A': 'var(--leaf-bright)', 'Series B': 'var(--leaf)', 'Series C': 'var(--moss)', 'Series D': 'var(--moss-deep)', 'Series D+': 'var(--moss-deep)', 'IPO': 'var(--gold)', 'Growth Equity': 'var(--sky)', 'Funding': 'var(--sky)' };
    const stageColor = stageColors[c.stage] || 'var(--text-dim)';
    const needs = (c.needs || []).slice(0, 4);
    const isHighQuality = c.source_quality === 'high';

    return `
      <div class="card" style="border-left:3px solid ${stageColor}">
        <div class="flex-between mb-8">
          <strong style="font-size:14px">${c.name || 'Unknown'}</strong>
          <div class="flex-center gap-6">
            <span class="tag" style="background:${stageColor}18;border-color:${stageColor}44;color:${stageColor};font-weight:600">${c.stage || 'Funding'}</span>
            <span style="font-size:10px;color:var(--text-dim)">${c.state || 'US'}</span>
          </div>
        </div>
        <div style="font-size:22px;font-weight:700;color:var(--moss);margin-bottom:4px">${c.total_funding_display || App.numFmt(amount)}</div>
        <div style="font-size:11px;color:var(--text-soft);margin-bottom:8px">${c.focus || ''}</div>
        <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px">
          ${needs.map(n => `<span class="tag tag-accent" style="font-size:9px">${n}</span>`).join('')}
        </div>
        <div class="flex-between">
          <span style="font-size:10px;color:var(--text-dim)">${c.source || ''}</span>
          ${c.url ? `<a href="${c.url}" target="_blank" style="font-size:10px;color:var(--moss)">Details →</a>` : ''}
        </div>
      </div>
    `;
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // SETUP
  // ═══════════════════════════════════════════════════════════════════════════

  setupListeners() {
    // ── View Tabs ───────────────────────────────────────────────────
    this.filters = this.filters || { keyword: '', state: '', stage: '' };

    document.querySelectorAll('.view-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const mode = tab.dataset.view;
        this.viewMode = mode;

        document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        const researcherView = document.getElementById('cb-researcher-view');
        const leaderboardView = document.getElementById('cb-leaderboard-view');
        const fundingView = document.getElementById('cb-funding-view');
        if (researcherView) researcherView.style.display = mode === 'researchers' ? 'flex' : 'none';
        if (leaderboardView) leaderboardView.style.display = mode === 'leaderboard' ? '' : 'none';
        if (fundingView) fundingView.style.display = mode === 'funding' ? '' : 'none';
        this._closeDetail();
      });
    });

    // ── SciLeads Search ─────────────────────────────────────────────
    document.getElementById('cb-sl-search-btn')?.addEventListener('click', () => this._doSciLeadsSearch());

    // ── Leaderboard ─────────────────────────────────────────────────
    document.getElementById('cb-lb-search-btn')?.addEventListener('click', () => this._doLeaderboard());
    document.getElementById('cb-lb-reset-btn')?.addEventListener('click', () => {
      const input = document.getElementById('cb-lb-search');
      const results = document.getElementById('cb-lb-results');
      if (input) input.value = '';
      if (results) results.innerHTML = `<div class="empty-state" style="padding:40px"><div class="empty-state-icon">🏆</div><div class="empty-state-title">Priority Leaderboard</div><div class="empty-state-desc">Enter a keyword above to rank all matching researchers by BD priority score</div></div>`;
    });
    document.getElementById('cb-lb-search')?.addEventListener('keydown', e => {
      if (e.key === 'Enter') this._doLeaderboard();
    });

    // ── Refresh ────────────────────────────────────────────────────
    document.getElementById('cb-refresh-btn')?.addEventListener('click', async () => {
      this.filters.keyword = document.getElementById('cb-keyword')?.value || '';
      this.filters.state = document.getElementById('cb-state')?.value || '';
      this.filters.stage = document.getElementById('cb-stage')?.value || '';
      await this.loadCompanies();
      this.renderCompanies();
      this._updateStatusBadge();
      this._updateBanner();
      App.showToast('Data refreshed', 'success');
    });

    // ── Funding Filters ────────────────────────────────────────────
    document.getElementById('cb-keyword')?.addEventListener('input', e => {
      this.filters.keyword = e.target.value;
      this.renderCompanies();
    });
    document.getElementById('cb-state')?.addEventListener('change', e => {
      this.filters.state = e.target.value;
      this.renderCompanies();
    });
    document.getElementById('cb-stage')?.addEventListener('change', e => {
      this.filters.stage = e.target.value;
      this.renderCompanies();
    });
  },
};
