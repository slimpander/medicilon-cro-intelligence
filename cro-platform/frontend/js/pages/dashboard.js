/**
 * Dashboard Page — BD Command Center
 * Sections: News, Patent Search, LinkedIn Activity, Medicilon Movements
 */
const PageDashboard = {
  patentResults: [],

  async render(container) {
    container.innerHTML = `
      <div class="page-header flex-between">
        <div>
          <div class="page-title">BD Command Center</div>
          <div class="page-subtitle">News · Patents · LinkedIn · Company Updates</div>
        </div>
        <button class="btn btn-primary" id="dash-report-btn" title="Generate daily intelligence report">📋 Daily Report</button>
      </div>

      <!-- ═══ SECTION 1: NEWS FEED ═══ -->
      <div class="card mb-16">
        <div class="card-header">
          <div class="card-title">📰 Latest CRO & Biotech News</div>
          <button class="btn btn-sm" onclick="App.navigate('news')">All News →</button>
        </div>
        <div id="dash-news-list" style="max-height:360px;overflow-y:auto">
          <div class="empty-state"><div class="empty-state-desc">Loading news...</div></div>
        </div>
      </div>

      <!-- ═══ SECTION 2: PATENT SEARCH ENGINE ═══ -->
      <div class="card mb-16">
        <div class="card-header">
          <div class="card-title">🔬 Patent Search Engine</div>
          <span style="font-size:10px;color:var(--text-dim)">Search USPTO · WIPO · Google Patents</span>
        </div>
        <div style="padding:12px 16px">
          <div class="flex-center gap-8" style="margin-bottom:12px">
            <input type="text" class="form-input" id="patent-search-input"
                   placeholder="Search patents... (e.g., DMPK LC-MS, antibody drug conjugate, PROTAC)"
                   style="flex:1;font-size:14px;padding:10px 14px">
            <select class="form-input" id="patent-search-source" style="max-width:160px">
              <option value="google">Google Patents</option>
            </select>
            <select class="form-input" id="patent-search-limit" style="max-width:80px">
              <option value="5">5</option>
              <option value="8" selected>8</option>
              <option value="12">12</option>
              <option value="20">20</option>
            </select>
            <button class="btn btn-primary" id="patent-search-btn">🔍 Search</button>
          </div>
          <div class="flex-between" style="margin-bottom:8px">
            <span style="font-size:11px;color:var(--text-dim)">Trending: <span id="patent-trending"></span></span>
            <span style="font-size:11px;color:var(--text-dim)" id="patent-count"></span>
          </div>
          <div id="patent-abbrev-indicator" style="display:none;font-size:11px;padding:6px 10px;background:var(--surface2);border-radius:var(--radius-sm);margin-bottom:8px;border-left:3px solid var(--accent)"></div>
          <div id="patent-results">
            <div class="empty-state" style="padding:20px">
              <div class="empty-state-icon">🔬</div>
              <div class="empty-state-title">Search patents by keyword, company, or technology area</div>
              <div class="empty-state-desc">Try: preclinical CRO, bioanalysis method, small molecule DMPK</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ SECTION 3: LINKEDIN TOP ACTIVITIES ═══ -->
      <div class="card mb-16">
        <div class="card-header">
          <div class="card-title">🔗 LinkedIn Top Activity</div>
          <button class="btn btn-sm" onclick="App.navigate('linkedin')">LinkedIn Monitor →</button>
        </div>
        <div id="dash-linkedin-list" style="max-height:300px;overflow-y:auto">
          <div class="empty-state"><div class="empty-state-desc">Loading LinkedIn data...</div></div>
        </div>
        <!-- Recommended Clients sub-panel -->
        <div style="border-top:1px solid var(--border-dim);margin-top:12px;padding-top:12px">
          <div class="card-header mb-8">
            <div class="card-title" style="font-size:13px">🎯 Recommended Potential Clients</div>
            <span style="font-size:10px;color:var(--text-dim)">AI analysis</span>
          </div>
          <div id="dash-recommend-list" style="max-height:240px;overflow-y:auto">
            <div class="empty-state"><div class="empty-state-desc">Based on LinkedIn signals...</div></div>
          </div>
        </div>
      </div>

      <!-- ═══ SECTION 4a: SCILEADS RESEARCH ═══ -->
      <div class="card mb-16 admin-only" style="display:none">
        <div class="card-header">
          <div class="card-title">🔬 SciLeads — Top Researchers</div>
          <span style="font-size:10px;color:var(--text-dim)" id="dash-scileads-badge"></span>
        </div>
        <div id="dash-scileads-list" style="max-height:300px;overflow-y:auto">
          <div class="empty-state"><div class="empty-state-desc">Connect SciLeads token in Settings to see researcher data...</div></div>
        </div>
      </div>

      <!-- ═══ SECTION 4b: CRUNCHBASE FUNDING HEADLINES ═══ -->
      <div class="card mb-16">
        <div class="card-header">
          <div class="card-title">💰 Crunchbase — Recent Funding Headlines</div>
          <button class="btn btn-sm" onclick="App.navigate('leads')">All Leads →</button>
        </div>
        <div id="dash-crunchbase-list" style="max-height:300px;overflow-y:auto">
          <div class="empty-state"><div class="empty-state-desc">Loading funding data...</div></div>
        </div>
      </div>

      <!-- ═══ SECTION 5: PITCHBOOK DEAL FLOW ═══ -->
      <div class="card mb-16">
        <div class="card-header">
          <div class="card-title">📊 PitchBook — Recent CRO / Biotech Deals</div>
          <span style="font-size:10px;color:var(--text-dim)">M&A · VC/PE · IPO</span>
        </div>
        <div id="dash-pitchbook-list" style="max-height:300px;overflow-y:auto">
          <div class="empty-state"><div class="empty-state-desc">Loading deal data...</div></div>
        </div>
      </div>

      <!-- ═══ SECTION 6: REMOVED — Medicilon panel overlapped with News feed ═══ -->
    `;

    await this.renderNews();
    await this.renderLinkedIn();
    await this.renderRecommendations();
    if (App.isAdmin) await this.renderSciLeads();
    await this.renderCrunchbase();
    await this.renderPitchBook();
    this.setupPatentSearch();

    // Wire Daily Report button
    document.getElementById('dash-report-btn')?.addEventListener('click', () => this.generateDailyReport());
  },

  // ═══ NEWS ════════════════════════════════════════════════════════
  async renderNews() {
    const el = document.getElementById('dash-news-list');
    if (!el) return;

    // Try to load from API or cached data
    let articles = App.newsData?.articles || [];
    if (!articles.length) {
      el.innerHTML = `<div class="empty-state" style="padding:20px">
        <div class="empty-state-desc">No news articles available.</div>
        <button class="btn btn-sm mt-8" id="dash-refresh-news-btn">🔄 Refresh News</button>
      </div>`;
      
      document.getElementById('dash-refresh-news-btn')?.addEventListener('click', async (e) => {
        e.target.disabled = true;
        App.showToast('Fetching latest news...', 'info');
        try {
          const r = await App.apiFetch(`${App.apiBase}/refresh/news`, { method: 'POST' });
          if (r.ok) {
            await App.loadData();
            this.renderNews();
          }
        } catch (err) {
          App.showToast('News refresh failed', 'error');
        }
        e.target.disabled = false;
      });
      return;
    }

    if (!articles.length) {
      el.innerHTML = `<div class="empty-state" style="padding:20px">
        <div class="empty-state-desc">No news loaded. Run fetch_news.py or connect NewsAPI.</div>
      </div>`;
      return;
    }

    const recent = articles
      .sort((a, b) => new Date(b.date_iso || 0) - new Date(a.date_iso || 0))
      .slice(0, 8);

    el.innerHTML = recent.map((a, i) => {
      const tags = (a.tags || []).slice(0, 3).map(t =>
        `<span class="tag tag-default" style="font-size:9px">${t}</span>`
      ).join('');
      const url = a.url || a.link || '';
      const hasLink = !!url;

      return `
        <div class="dash-news-item" style="padding:10px 0;border-bottom:1px solid var(--border-dim);${i === 0 ? '' : ''}">
          <div class="flex-between mb-4">
            <strong style="font-size:13px;line-height:1.4;flex:1;${hasLink ? 'cursor:pointer;color:var(--accent)' : ''}"
                    ${hasLink ? `onclick="window.open('${url.replace(/'/g, "\\'")}','_blank')" title="Click to read full article"` : ''}>
              ${hasLink ? '<span style="font-size:10px">🔗 </span>' : ''}${a.title || 'Untitled'}
            </strong>
            <span style="font-size:10px;color:var(--text-dim);white-space:nowrap;margin-left:8px">${App.relativeDate(a.date_iso) || a.date || ''}</span>
          </div>
          ${a.summary ? `<div style="font-size:11px;color:var(--text-muted);line-height:1.5;margin-bottom:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${a.summary}</div>` : ''}
          <div style="display:flex;align-items:center;gap:8px">
            ${tags}
            <span style="font-size:9px;color:var(--text-dim)">${a.source || ''}</span>
            ${hasLink ? `<a href="${url}" target="_blank" style="font-size:9px;color:var(--accent);text-decoration:none;margin-left:auto">Read article →</a>` : ''}
          </div>
        </div>
      `;
    }).join('');
  },

  // ═══ PATENT SEARCH ═══════════════════════════════════════════════
  setupPatentSearch() {
    // Trending quick-search tags
    const trending = ['ADC', 'DMPK LC-MS/MS', 'PROTAC', 'CRISPR delivery', 'bispecific antibody', 'gene therapy AAV'];
    const trendingEl = document.getElementById('patent-trending');
    if (trendingEl) {
      trendingEl.innerHTML = trending.map(t =>
        `<span class="tag tag-default" style="cursor:pointer;font-size:10px;margin:0 2px"
              onclick="document.getElementById('patent-search-input').value='${t}';PageDashboard.doPatentSearch()">${t}</span>`
      ).join('');
    }

    document.getElementById('patent-search-btn')?.addEventListener('click', () => this.doPatentSearch());
    document.getElementById('patent-search-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.doPatentSearch();
    });
  },

  async doPatentSearch() {
    const input = document.getElementById('patent-search-input');
    const resultsEl = document.getElementById('patent-results');
    const countEl = document.getElementById('patent-count');
    const query = input?.value?.trim();

    if (!query) {
      App.showToast('Enter a search term', 'error');
      return;
    }

    resultsEl.innerHTML = '<div class="empty-state" style="padding:20px"><div class="loader-spinner"></div><div class="empty-state-desc">Searching patents...</div></div>';
    if (countEl) countEl.textContent = '';
    const abbrevEl = document.getElementById('patent-abbrev-indicator');
    if (abbrevEl) abbrevEl.style.display = 'none';

    try {
      // Try backend proxy first
      const r = await fetch(`${App.apiBase}/patents/search?q=${encodeURIComponent(query)}&source=google&limit=${document.getElementById('patent-search-limit')?.value || 8}`);
      if (!r.ok) throw new Error('API unavailable');
      const data = await r.json();

      this.patentResults = data.results || [];
      this.renderPatentResults(data);

      // Show abbreviation expansion indicator
      if (data.abbreviations_expanded && data.abbreviations_expanded.length > 0) {
        const indicator = document.getElementById('patent-abbrev-indicator');
        if (indicator) {
          indicator.innerHTML = `<span style="color:var(--accent);font-weight:600">🔬 Auto-scoped to biopharma:</span> ${data.abbreviations_expanded.join(' · ')}`;
          indicator.style.display = 'block';
        }
      }
    } catch (e) {
      // Fallback: open Google Patents in new tab
      console.warn('[Patent] Backend unavailable, using direct search');
      resultsEl.innerHTML = `
        <div style="text-align:center;padding:20px">
          <p style="font-size:13px;color:var(--text-dim);margin-bottom:12px">Patent search backend not available</p>
          <a href="https://patents.google.com/?q=${encodeURIComponent(query)}" target="_blank"
             class="btn btn-primary" style="display:inline-block;text-decoration:none">
            🔍 Search on Google Patents →
          </a>
          <p style="font-size:10px;color:var(--text-dim);margin-top:8px">
            Start the backend server for inline patent results
          </p>
        </div>
      `;
      if (countEl) countEl.textContent = '';
    }
  },

  renderPatentResults(data) {
    const resultsEl = document.getElementById('patent-results');
    const countEl = document.getElementById('patent-count');
    const results = data.results || [];

    if (countEl) countEl.textContent = `${data.total || results.length} results`;

    if (!results.length) {
      resultsEl.innerHTML = `<div class="empty-state" style="padding:20px">
        <div class="empty-state-desc">No patents found for "${data.query || ''}"</div>
      </div>`;
      return;
    }

    resultsEl.innerHTML = results.slice(0, 8).map((p, i) => {
      const url = p.url || p.patent_url || `https://patents.google.com/patent/${p.patent_number}/en`;
      const title = p.title || p.patent_title || 'Untitled Patent';
      const number = p.patent_number || '';
      const assignee = p.assignee || p.assignee_organization || '';
      const date = p.date || p.grant_date || p.publication_date || '';
      const abstract = (p.abstract || p.summary || '').slice(0, 200);

      return `
        <div class="dash-news-item" style="padding:10px 0;border-bottom:1px solid var(--border-dim)">
          <div class="flex-between mb-4">
            <strong style="font-size:12px;line-height:1.4;flex:1;cursor:pointer;color:var(--accent)"
                    onclick="window.open('${url}','_blank')">
              🔗 ${title}
            </strong>
            ${number ? `<span class="tag tag-default" style="font-size:9px;white-space:nowrap;margin-left:8px">${number}</span>` : ''}
          </div>
          <div class="flex-between" style="font-size:10px;color:var(--text-dim);margin-bottom:4px">
            <span>${assignee || 'Unknown assignee'}</span>
            <span>${date ? App.relativeDate(date) : ''}</span>
          </div>
          ${abstract ? `<div style="font-size:11px;color:var(--text-muted);line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${abstract}</div>` : ''}
          ${i === 0 && results.length > 1 ? '<div style="font-size:10px;color:var(--gold);margin-top:4px">⭐ Top result — most relevant</div>' : ''}
        </div>
      `;
    }).join('');
  },

  // ═══ LINKEDIN ACTIVITY ═══════════════════════════════════════════
  async renderLinkedIn() {
    const el = document.getElementById('dash-linkedin-list');
    if (!el) return;

    try {
      const [statsR, postsR] = await Promise.allSettled([
        fetch(`${App.apiBase}/linkedin/stats`),
        fetch(`${App.apiBase}/linkedin/posts?limit=10&min_score=0`),
      ]);

      const stats = (statsR.status === 'fulfilled' && statsR.value.ok) ? await statsR.value.json() : null;
      const posts = (postsR.status === 'fulfilled' && postsR.value.ok) ? await postsR.value.json() : [];

      // ── DB is empty or no posts returned: fall back to aggregated JSON ─────────
      if (!stats || stats.total_posts === 0 || !posts.length) {
        const aggR = await fetch(`${App.apiBase}/linkedin/aggregated?limit=20`);
        if (!aggR.ok) throw new Error('No aggregated data');
        const agg = await aggR.json();
        const leads = (agg.leads || []).sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
        if (!leads.length) throw new Error('Empty feed');

        const tierColor = { S: 'var(--green)', A: 'var(--accent)', B: 'var(--gold)', C: 'var(--text-muted)', D: 'var(--text-dim)' };
        const highCount = leads.filter(l => (l.relevance_score || 0) >= 70).length;
        const avgScore  = Math.round(leads.reduce((s, l) => s + (l.relevance_score || 0), 0) / leads.length);

        el.innerHTML = `
          <div style="display:flex;align-items:center;gap:8px;padding:8px 16px;border-bottom:1px solid var(--border-dim)">
            <span class="tag" style="background:rgba(0,212,255,0.1);border-color:rgba(0,212,255,0.3);color:var(--accent);font-size:9px">📡 Aggregated Feed</span>
            <span style="font-size:10px;color:var(--text-dim)">${leads.length} signals · ${highCount} high-priority · avg ${avgScore}</span>
            <button class="btn btn-sm" style="margin-left:auto;font-size:10px;padding:2px 8px" onclick="PageDashboard.renderLinkedIn()">↻</button>
          </div>
          <div style="display:flex;gap:12px;padding:10px 16px">
            <div style="flex:1;text-align:center;padding:10px;background:var(--surface2);border-radius:8px">
              <div style="font-size:20px;font-weight:700;color:var(--accent)">${highCount}</div>
              <div style="font-size:10px;color:var(--text-dim)">High Priority</div>
            </div>
            <div style="flex:1;text-align:center;padding:10px;background:var(--surface2);border-radius:8px">
              <div style="font-size:20px;font-weight:700;color:var(--gold)">${leads.filter(l => l.tier === 'S' || l.tier === 'A').length}</div>
              <div style="font-size:10px;color:var(--text-dim)">Tier S / A</div>
            </div>
            <div style="flex:1;text-align:center;padding:10px;background:var(--surface2);border-radius:8px">
              <div style="font-size:20px;font-weight:700;color:var(--green)">${avgScore}</div>
              <div style="font-size:10px;color:var(--text-dim)">Avg Score</div>
            </div>
          </div>
          ${leads.slice(0, 4).map(p => `
            <div class="dash-news-item" style="padding:8px 16px;border-top:1px solid var(--border-dim);cursor:pointer" onclick="App.navigate('linkedin')">
              <div class="flex-between mb-4">
                <strong style="font-size:12px;flex:1;line-height:1.3">${p.title || (p.content || '').slice(0, 80) || 'Signal'}</strong>
                <span style="font-size:10px;font-weight:600;padding:1px 6px;border-radius:3px;margin-left:8px;white-space:nowrap;
                  background:${(tierColor[p.tier] || 'var(--text-dim)')}22;
                  color:${tierColor[p.tier] || 'var(--text-dim)'};
                  border:1px solid ${(tierColor[p.tier] || 'var(--text-dim)')}44">
                  ${p.tier || '—'} · ${Math.round(p.relevance_score || 0)}
                </span>
              </div>
              <div style="font-size:11px;color:var(--text-muted);line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${(p.content || '').slice(0, 140)}</div>
              <div style="display:flex;gap:8px;margin-top:4px;align-items:center">
                <span style="font-size:9px;color:var(--text-dim)">${p.source || ''}</span>
                <span style="font-size:9px;color:var(--text-dim)">${App.relativeDate(p.date)}</span>
                ${p.matched_keywords ? `<span style="font-size:9px;color:var(--accent);opacity:.7">${p.matched_keywords.split(',').slice(0, 3).join(' · ')}</span>` : ''}
                ${p.url ? `<a href="${p.url}" target="_blank" onclick="event.stopPropagation()" style="font-size:9px;color:var(--accent);text-decoration:none;margin-left:auto">↗</a>` : ''}
              </div>
            </div>
          `).join('')}
          <div style="padding:10px 16px;text-align:center">
            <button class="btn btn-sm btn-primary" onclick="App.navigate('linkedin')">View All ${leads.length} BD Signals →</button>
          </div>
        `;
        return;
      }

      // ── DB has data: render from linkedin_posts table ──────────────────────────
      el.innerHTML = `
        <div style="display:flex;gap:16px;padding:12px 16px">
          <div style="flex:1;text-align:center;padding:12px;background:var(--surface2);border-radius:8px">
            <div style="font-size:22px;font-weight:700;color:var(--accent)">${stats.high_priority || 0}</div>
            <div style="font-size:10px;color:var(--text-dim)">High Priority Posts</div>
          </div>
          <div style="flex:1;text-align:center;padding:12px;background:var(--surface2);border-radius:8px">
            <div style="font-size:22px;font-weight:700;color:var(--green)">${stats.total_contacts || 0}</div>
            <div style="font-size:10px;color:var(--text-dim)">Decision Makers</div>
          </div>
          <div style="flex:1;text-align:center;padding:12px;background:var(--surface2);border-radius:8px">
            <div style="font-size:22px;font-weight:700;color:var(--gold)">${stats.avg_relevance || 0}</div>
            <div style="font-size:10px;color:var(--text-dim)">Avg Relevance</div>
          </div>
        </div>
        ${posts.slice(0, 4).map(p => {
          const score = Math.round(p.relevance_score || 0);
          const scoreColor = score >= 70 ? 'var(--green)' : score >= 40 ? 'var(--accent)' : 'var(--text-dim)';
          // DB posts have no title field; extract from content (strip [Source] prefix)
          const rawContent = p.content || '';
          const title = p.title || p.author_name ||
            rawContent.replace(/^\[.*?\]\s*/, '').split('\n')[0].slice(0, 90) || 'BD Signal';
          const subtitle = p.author_title ? `<div style="font-size:10px;color:var(--accent);margin-bottom:2px">${p.author_title}${p.author_company ? ' · ' + p.author_company : ''}</div>` : '';
          return `
          <div class="dash-news-item" style="padding:8px 16px;border-top:1px solid var(--border-dim);cursor:pointer" onclick="App.navigate('linkedin')">
            <div class="flex-between mb-4">
              <strong style="font-size:12px;flex:1;line-height:1.3">${title}</strong>
              <span style="font-size:10px;font-weight:600;padding:1px 7px;border-radius:3px;margin-left:8px;white-space:nowrap;background:${scoreColor}22;color:${scoreColor};border:1px solid ${scoreColor}44">${score}</span>
            </div>
            ${subtitle}
            <div style="font-size:11px;color:var(--text-muted);line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${(p.content || '').slice(0, 140)}</div>
            <div style="font-size:9px;color:var(--text-dim);margin-top:4px">${(p.matched_keywords || '').split(',').slice(0,4).join(' · ')}</div>
          </div>`;
        }).join('')}
        <div style="padding:8px 16px;text-align:center">
          <button class="btn btn-sm btn-primary" onclick="App.navigate('linkedin')">View All ${stats.total_posts} BD Signals →</button>
        </div>
      `;
    } catch (e) {
      console.log('[Dashboard] LinkedIn error:', e.message);
      el.innerHTML = `
        <div class="empty-state" style="padding:20px">
          <div class="empty-state-icon">🔗</div>
          <div class="empty-state-title">BD Intel Feed</div>
          <div class="empty-state-desc">Start the backend server to load BD intelligence signals</div>
          <button class="btn btn-sm btn-primary mt-8" onclick="App.navigate('linkedin')">Open BD Intel Feed →</button>
        </div>
      `;
    }
  },

  // ═══ MEDICILON MOVEMENTS ═════════════════════════════════════════
  // SciLeads research — admin-only, OFF by default (explicit connect required)
  async renderSciLeads() {
    const el = document.getElementById('dash-scileads-list');
    const badge = document.getElementById('dash-scileads-badge');
    if (!el) return;

    el.innerHTML = `<div class="empty-state" style="padding:20px">
      <div class="empty-state-icon">🔬</div>
      <div class="empty-state-title">SciLeads — Offline</div>
      <div class="empty-state-desc">Connection is off by default. Click below to fetch researcher data.</div>
      <button class="btn btn-sm btn-primary mt-8" id="dash-scileads-connect-btn">🔌 Connect SciLeads</button>
    </div>`;
    if (badge) badge.innerHTML = '<span style="color:var(--text-dim)">⬤ Offline</span>';

    // Wire connect button
    document.getElementById('dash-scileads-connect-btn')?.addEventListener('click', () => this._doSciLeadsFetch());
  },

  async _doSciLeadsFetch() {
    const el = document.getElementById('dash-scileads-list');
    const badge = document.getElementById('dash-scileads-badge');
    if (!el) return;

    // Check if token is configured
    let hasToken = App.settings?.scilead_token || localStorage.getItem('scilead_token');

    if (!hasToken && App.user) {
      try {
        const sr = await App.apiFetch(`${App.apiBase}/settings`);
        if (sr.ok) {
          App.settings = await sr.json();
          hasToken = App.settings?.scilead_token;
        }
      } catch(e) {}
    }

    if (!hasToken) {
      el.innerHTML = `<div class="empty-state" style="padding:20px">
        <div class="empty-state-icon">🔬</div>
        <div class="empty-state-title">SciLeads Not Configured</div>
        <div class="empty-state-desc">Paste your Bearer token in Settings to enable researcher data</div>
        <button class="btn btn-sm btn-primary mt-8" onclick="App.navigate('settings')">⚙️ Configure SciLeads →</button>
        <button class="btn btn-sm mt-4" onclick="PageDashboard._backToOffline()">← Back to offline</button>
      </div>`;
      if (badge) badge.innerHTML = '<span style="color:var(--text-dim)">⬤ Not configured</span>';
      return;
    }

    el.innerHTML = '<div class="empty-state" style="padding:20px"><div class="loader-spinner"></div><div class="empty-state-desc">Connecting to SciLeads...</div></div>';
    if (badge) badge.innerHTML = '<span style="color:var(--gold)">● Connecting...</span>';

    try {
      const searchTerms = ['biotech', 'oncology', 'clinical trial', 'drug development', 'CRO'];
      const kw = searchTerms[Math.floor(Math.random() * searchTerms.length)];
      const r = await App.apiFetch(`${App.apiBase}/scilead/search?keyword=${encodeURIComponent(kw)}&count=20&categories=Publications,ClinicalTrials,Funding,Tradeshows`);
      if (!r.ok) {
        if (r.status === 401) {
          el.innerHTML = `<div class="empty-state" style="padding:20px">
            <div class="empty-state-icon">⚠️</div>
            <div class="empty-state-title">Token Expired</div>
            <div class="empty-state-desc">Your SciLeads token has expired. Get a new one from DevTools → Network.</div>
            <button class="btn btn-sm btn-primary mt-8" onclick="App.navigate('settings')">⚙️ Update Token →</button>
            <button class="btn btn-sm mt-4" onclick="PageDashboard._backToOffline()">← Back to offline</button>
          </div>`;
          if (badge) badge.innerHTML = '<span style="color:var(--red)">⬤ Expired</span>';
        }
        throw new Error('API error');
      }

      const data = await r.json();
      const researchers = data.researchers || [];

      if (!researchers.length) throw new Error('No data');

      const industry = researchers.filter(r =>
        r.company_type?.includes('Industry') || r.company?.match(/bms|pfizer|novartis|roche|merck|astrazeneca|gsk|sanofi|jnj|abbvie|gilead|amgen|regeneron|lilly/i)
      ).slice(0, 3);

      const kols = researchers
        .filter(r => r.h_index_3yr >= 30)
        .sort((a, b) => b.h_index_3yr - a.h_index_3yr)
        .slice(0, 5);

      if (badge && data.total_results) badge.innerHTML = `<span style="color:var(--leaf)">● ${data.total_results?.toLocaleString() || '?'} results</span>`;

      let html = '';

      // Quick stats bar
      if (data.total_results) {
        html += `<div style="display:flex;gap:12px;padding:10px 16px;flex-wrap:wrap">
          <div style="flex:1;min-width:100px;text-align:center;padding:8px;background:var(--surface2);border-radius:6px">
            <div style="font-size:18px;font-weight:700;color:var(--accent)">${(data.total_results || 0).toLocaleString()}</div>
            <div style="font-size:10px;color:var(--text-dim)">Total Records</div>
          </div>
          <div style="flex:1;min-width:100px;text-align:center;padding:8px;background:var(--surface2);border-radius:6px">
            <div style="font-size:18px;font-weight:700;color:var(--green)">${(data.visualisations?.totalPublications || 0).toLocaleString()}</div>
            <div style="font-size:10px;color:var(--text-dim)">Publications</div>
          </div>
          <div style="flex:1;min-width:100px;text-align:center;padding:8px;background:var(--surface2);border-radius:6px">
            <div style="font-size:18px;font-weight:700;color:var(--gold)">${industry.length}</div>
            <div style="font-size:10px;color:var(--text-dim)">Industry Contacts</div>
          </div>
          <div style="flex:1;min-width:100px;text-align:center;padding:8px;background:var(--surface2);border-radius:6px">
            <div style="font-size:18px;font-weight:700;color:var(--purple)">${kols.length}</div>
            <div style="font-size:10px;color:var(--text-dim)">Top KOLs</div>
          </div>
        </div>`;
      }

      // Industry contacts spotlight
      if (industry.length) {
        html += `<div style="padding:4px 16px 8px"><strong style="font-size:11px;color:var(--text-soft);text-transform:uppercase;letter-spacing:.05em">🏢 Industry Contacts</strong></div>`;
        html += industry.map(r => `
          <div class="dash-news-item" style="padding:8px 16px;border-top:1px solid var(--border-dim);cursor:pointer"
               onclick="App.navigate('crunchbase')">
            <div class="flex-between mb-4">
              <strong style="font-size:12px;flex:1">${r.name}</strong>
              <span style="font-size:10px;font-weight:600;padding:1px 6px;border-radius:3px;margin-left:8px;white-space:nowrap;color:${r.email_quality==='SafeToSend'?'var(--green)':'var(--gold)'};background:${r.email_quality==='SafeToSend'?'rgba(46,204,113,0.1)':'rgba(241,196,15,0.1)'}">
                ${r.email_quality === 'SafeToSend' ? '✅' : '⚠️'} ${r.email_quality || 'Unknown'}
              </span>
            </div>
            <div style="font-size:10px;color:var(--accent);margin-bottom:2px">${r.title || ''}${r.company ? ' · ' + r.company : ''}</div>
            <div style="font-size:11px;color:var(--text-muted);line-height:1.4">${r.email || ''}${r.linkedin ? ' · 🔗 LinkedIn' : ''}${r.country ? ' · ' + r.country : ''}</div>
          </div>
        `).join('');
      }

      // KOL spotlight
      if (kols.length) {
        html += `<div style="padding:4px 16px 8px;margin-top:4px"><strong style="font-size:11px;color:var(--text-soft);text-transform:uppercase;letter-spacing:.05em">🎓 Top KOLs</strong></div>`;
        html += kols.map(r => `
          <div class="dash-news-item" style="padding:8px 16px;border-top:1px solid var(--border-dim);cursor:pointer"
               onclick="App.navigate('crunchbase')">
            <div class="flex-between mb-4">
              <strong style="font-size:12px;flex:1">${r.name}</strong>
              <span style="font-size:11px;font-weight:700;color:var(--purple);white-space:nowrap;margin-left:8px">H-index ${r.h_index_3yr || '?'}</span>
            </div>
            <div style="font-size:10px;color:var(--accent);margin-bottom:2px">${r.institution || r.company || ''}${r.country ? ' · ' + r.country : ''}</div>
            <div style="font-size:10px;color:var(--text-dim);display:flex;gap:10px;flex-wrap:wrap">
              <span>📄 ${r.total_publications || 0} pubs</span>
              ${r.total_clinical_trials ? `<span>🧪 ${r.total_clinical_trials} trials</span>` : ''}
              ${r.top_mesh?.length ? `<span>🔬 ${r.top_mesh.slice(0, 3).map(m => m.replace(/#\d+$/, '')).join(' · ')}</span>` : ''}
            </div>
          </div>
        `).join('');
      }

      html += `<div style="padding:8px 16px;text-align:center">
        <button class="btn btn-sm btn-primary" onclick="App.navigate('crunchbase')">🔍 Search SciLeads Researchers →</button>
      </div>`;

      el.innerHTML = html;
    } catch (e) {
      console.log('[Dashboard] SciLeads:', e.message);
      el.innerHTML = `<div class="empty-state" style="padding:20px">
        <div class="empty-state-icon">📡</div>
        <div class="empty-state-title">Connection Failed</div>
        <div class="empty-state-desc">Backend may be offline or token may need refreshing.</div>
        <span style="font-size:10px;color:var(--text-dim)">${e.message}</span>
        <button class="btn btn-sm mt-8" onclick="PageDashboard._backToOffline()">← Back to offline</button>
      </div>`;
      if (badge) badge.innerHTML = '<span style="color:var(--red)">⬤ Error</span>';
    }
  },

  _backToOffline() {
    const el = document.getElementById('dash-scileads-list');
    const badge = document.getElementById('dash-scileads-badge');
    if (!el) return;
    el.innerHTML = `<div class="empty-state" style="padding:20px">
      <div class="empty-state-icon">🔬</div>
      <div class="empty-state-title">SciLeads — Offline</div>
      <div class="empty-state-desc">Connection is off by default. Click below to fetch researcher data.</div>
      <button class="btn btn-sm btn-primary mt-8" id="dash-scileads-connect-btn">🔌 Connect SciLeads</button>
    </div>`;
    if (badge) badge.innerHTML = '<span style="color:var(--text-dim)">⬤ Offline</span>';
    document.getElementById('dash-scileads-connect-btn')?.addEventListener('click', () => this._doSciLeadsFetch());
  },

  // ═══ CRUNCHBASE HEADLINES ═══════════════════════════════════════════
  async renderCrunchbase() {
    const el = document.getElementById('dash-crunchbase-list');
    if (!el) return;

    try {
      const r = await App.apiFetch(`${App.apiBase}/crunchbase/recently-funded?days=90&limit=8`);
      if (!r.ok) throw new Error('Crunchbase data unavailable');
      const data = await r.json();
      const companies = data.leads || data.companies || [];

      if (!companies.length) throw new Error('No data');

      el.innerHTML = companies.slice(0, 6).map((c, i) => {
        const name = c.name || c.company_name || 'Unknown';
        const amount = c.total_funding_display || c.recent_round_amount_display || c.last_funding_amount || '';
        const desc = (c.description || c.focus || c.short_description || '').slice(0, 120);
        const stage = c.funding_stage || c.stage || '';
        const state = c.state || c.location || '';
        const url = c.url || c.website || c.permalink ? `https://crunchbase.com/organization/${c.permalink}` : '';

        return `
          <div class="dash-news-item" style="padding:10px 0;border-bottom:1px solid var(--border-dim);${i === 0 ? 'border-left:3px solid var(--accent);padding-left:12px' : ''}">
            <div class="flex-between mb-4">
              <strong style="font-size:13px;flex:1">${name}</strong>
              ${amount ? `<span style="font-size:14px;font-weight:700;color:var(--green);white-space:nowrap;margin-left:8px">${amount}</span>` : ''}
            </div>
            <div class="flex-between" style="font-size:10px;color:var(--text-dim);margin-bottom:4px">
              <span>${[stage, state].filter(Boolean).join(' · ')}</span>
              ${url ? `<a href="${url}" target="_blank" style="color:var(--accent);text-decoration:none;font-size:9px">Crunchbase →</a>` : ''}
            </div>
            ${desc ? `<div style="font-size:11px;color:var(--text-muted);line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${desc}</div>` : ''}
          </div>
        `;
      }).join('');
    } catch (e) {
      console.log('[Dashboard] Crunchbase:', e.message);
      el.innerHTML = `
        <div style="padding:20px;text-align:center">
          <p style="font-size:13px;color:var(--text-dim);margin-bottom:8px">Configure Crunchbase API key in Settings to see live funding data</p>
          <button class="btn btn-sm btn-primary" onclick="App.navigate('settings')">⚙️ Open Settings →</button>
        </div>
      `;
    }
  },

  // ═══ LINKEDIN CLIENT RECOMMENDATIONS ═════════════════════════════════
  async renderRecommendations() {
    const el = document.getElementById('dash-recommend-list');
    if (!el) return;

    try {
      const r = await fetch(`${App.apiBase}/linkedin/recommendations`);
      if (!r.ok) throw new Error('No data');
      const data = await r.json();
      const recs = data.recommendations || [];

      if (!recs.length) throw new Error('Empty');

      el.innerHTML = `
        <div style="display:flex;gap:12px;overflow-x:auto;padding:4px 0">
          ${recs.slice(0, 4).map(r => `
            <div style="min-width:200px;flex:1;background:var(--surface2);border-radius:var(--radius-sm);padding:12px;border:1px solid var(--border-dim)">
              <div class="flex-between mb-4">
                <strong style="font-size:12px">${r.company || r.name}</strong>
                <span class="tag tag-green" style="font-size:9px">${r.match_score || r.score}%</span>
              </div>
              ${r.contact_title ? `<div style="font-size:10px;color:var(--accent);margin-bottom:4px">${r.contact_title}</div>` : ''}
              <div style="font-size:10px;color:var(--text-muted);line-height:1.4;margin-bottom:6px">${r.reason || ''}</div>
              <div style="display:flex;flex-wrap:wrap;gap:2px">
                ${(r.signals || []).slice(0, 3).map(s => `<span class="tag tag-default" style="font-size:8px">${s}</span>`).join('')}
              </div>
            </div>
          `).join('')}
        </div>
      `;
    } catch (e) {
      console.log('[Dashboard] Recs:', e.message);
      el.innerHTML = `<div style="font-size:11px;color:var(--text-dim);padding:8px 0">Connect LinkedIn extension to generate client recommendations</div>`;
    }
  },

  // ═══ PITCHBOOK DEAL FLOW ══════════════════════════════════════════
  async renderPitchBook() {
    const el = document.getElementById('dash-pitchbook-list');
    if (!el) return;

    try {
      const r = await fetch(`${App.apiBase}/pitchbook/deals?limit=8`);
      if (!r.ok) throw new Error('No data');
      const data = await r.json();
      const deals = data.deals || [];

      if (!deals.length) throw new Error('Empty');

      const TYPE_COLORS = {
        'M&A': 'var(--accent)',
        'Series A': 'var(--green)',
        'Series B': 'var(--green)',
        'Series C': 'var(--green)',
        'Series D': 'var(--green)',
        'Growth Equity': 'var(--orange)',
        'Private Equity': 'var(--purple)',
        'IPO': 'var(--gold)',
      };

      el.innerHTML = deals.map((d, i) => {
        const tc = TYPE_COLORS[d.deal_type] || 'var(--text-dim)';
        return `
          <div class="dash-news-item" style="padding:10px 0;border-bottom:1px solid var(--border-dim);${i === 0 ? 'border-left:3px solid var(--accent);padding-left:12px' : ''}">
            <div class="flex-between mb-4">
              <div class="flex-center gap-8" style="flex:1">
                <span class="tag" style="background:${tc}15;border-color:${tc}33;color:${tc};font-size:9px;font-weight:600">${d.deal_type}</span>
                <strong style="font-size:12px">${d.target}</strong>
              </div>
              <span style="font-size:13px;font-weight:700;color:var(--accent);white-space:nowrap;margin-left:8px">${d.amount}</span>
            </div>
            <div style="font-size:10px;color:var(--text-dim);margin-bottom:4px">
              ${d.acquirer ? `${d.acquirer} acquires` : d.investors ? `Investors: ${d.investors}` : d.exchange || ''} · ${App.relativeDate(d.date)}
            </div>
            <div style="font-size:11px;color:var(--text-muted);line-height:1.4;margin-bottom:4px">${d.description}</div>
            <div style="font-size:10px;color:var(--purple);font-style:italic">💡 ${d.relevance}</div>
          </div>
        `;
      }).join('');
    } catch (e) {
      console.log('[Dashboard] PitchBook:', e.message);
      el.innerHTML = `
        <div style="padding:20px;text-align:center">
          <p style="font-size:13px;color:var(--text-dim);margin-bottom:4px">📊 PitchBook deal data</p>
          <p style="font-size:11px;color:var(--text-muted)">Connect PitchBook account in Settings for live deal flow</p>
        </div>
      `;
    }
  },

  // ═══ DAILY REPORT ═══════════════════════════════════════════════
  async generateDailyReport() {
    const overlay = document.createElement('div');
    overlay.className = 'report-overlay';
    overlay.id = 'report-overlay';
    overlay.innerHTML = `<div class="report-modal"><div class="report-header" style="text-align:center;padding:40px 28px 24px">
      <div class="loader-spinner" style="margin:0 auto"></div>
      <div style="margin-top:16px;font-size:13px;color:var(--text-dim)">Generating intelligence report...</div>
    </div></div>`;
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    document.body.appendChild(overlay);

    // Fetch all data sources in parallel
    const [analytics, newsData, dealsData, croData, intelData] = await Promise.allSettled([
      App.apiFetch(`${App.apiBase}/analytics/overview`).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('data/news_data.json').then(r => r.json()).catch(() => null),
      fetch('data/deals.json').then(r => r.json()).catch(() => null),
      fetch('data/cro_data.json').then(r => r.json()).catch(() => null),
      fetch('data/intelligence.json').then(r => r.json()).catch(() => null),
    ]);

    const a = analytics.status === 'fulfilled' ? analytics.value : null;
    const news = newsData.status === 'fulfilled' ? newsData.value : null;
    const deals = dealsData.status === 'fulfilled' ? dealsData.value : null;
    const cros = croData.status === 'fulfilled' ? croData.value : null;
    const intel = intelData.status === 'fulfilled' ? intelData.value : null;

    const now = new Date();
    const dateStr = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    // ── Helper: format tags ──────────────────────────────────────────
    const tags = (entries, cls = '') => entries.map(([k, v]) =>
      `<span class="rpt-tag ${cls}"><b>${k}</b>: ${v}</span>`).join('');
    const hl = (icon, text, sub = '') =>
      `<div class="report-highlight">${icon} <b>${text}</b>${sub ? `<br><span class="rpt-sub">${sub}</span>` : ''}</div>`;
    const pct = (v, t) => t > 0 ? ((v / t) * 100).toFixed(1) + '%' : '0%';

    // ── 1. EXECUTIVE SUMMARY ─────────────────────────────────────────
    let summaryHTML = '';
    if (a) {
      const topSrc = Object.entries(a.leads?.by_source || {}).sort((a,b) => b[1]-a[1])[0];
      const topStage = Object.entries(a.leads?.by_stage || {}).sort((a,b) => b[1]-a[1])[0];
      const topSvc = Object.entries(a.service_demand || {}).sort((a,b) => b[1]-a[1])[0];
      const topFocus = Object.entries(a.leads?.top_focus_areas || {}).sort((a,b) => b[1]-a[1])[0];
      summaryHTML = `
        <div class="report-stat-row">
          <div class="report-stat"><div class="stat-value">${a.totals.leads}</div><div class="stat-label">Active Leads</div></div>
          <div class="report-stat"><div class="stat-value">${a.totals.deals}</div><div class="stat-label">Tracked Deals</div></div>
          <div class="report-stat"><div class="stat-value">${a.totals.news_articles}</div><div class="stat-label">News Articles</div></div>
          <div class="report-stat"><div class="stat-value">${a.totals.linkedin_posts}</div><div class="stat-label">LinkedIn Signals</div></div>
        </div>
        <div class="report-analysis">
          <p>Today's intelligence covers <b>${a.totals.leads} active leads</b> across ${Object.keys(a.leads?.by_source || {}).length} sources.
          The primary lead source is <b>${topSrc ? topSrc[0] : 'N/A'}</b> (${topSrc ? topSrc[1] : 0} leads),
          with <b>${topStage ? topStage[0] : 'N/A'}</b> being the most common stage.
          Top CRO service demand is <b>${topSvc ? topSvc[0] : 'N/A'}</b> (${topSvc ? topSvc[1] : 0} requests).
          ${topFocus ? `The leading therapeutic focus area is <b>${topFocus[0]}</b>.` : ''}</p>
        </div>`;
    }

    // ── 2. LEAD INTELLIGENCE ─────────────────────────────────────────
    let leadsHTML = '';
    if (a) {
      const bySrc = Object.entries(a.leads?.by_source || {});
      const byStage = Object.entries(a.leads?.by_stage || {});
      const byState = Object.entries(a.leads?.by_state || {});
      const byFocus = Object.entries(a.leads?.top_focus_areas || {});

      // Top leads from intel data
      let topLeadsList = '';
      if (intel?.leads) {
        topLeadsList = intel.leads.slice(0, 6).map(l =>
          hl('🎯', `${l.name || l.title || 'Lead'}`, `${l.source} · ${l.stage || 'N/A'} · ${l.focus || ''}${l.state ? ' · ' + l.state : ''}`)
        ).join('');
      }

      // State distribution analysis
      const topState = byState[0];
      const hubStates = ['CA', 'MA', 'NJ', 'MD', 'NC', 'PA', 'NY', 'TX'];
      const hubCount = byState.filter(([s]) => hubStates.includes(s)).reduce((sum, [,c]) => sum + c, 0);

      leadsHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
          <div>
            <div class="rpt-subtitle">Lead Sources</div>
            ${bySrc.map(([k, v]) => `<div class="rpt-bar-row"><span class="rpt-bar-label">${k}</span><span class="rpt-bar-track"><span class="rpt-bar-fill" style="width:${(v/Math.max(...bySrc.map(x=>x[1])))*100}%;background:var(--primary)"></span></span><span class="rpt-bar-val">${v}</span></div>`).join('')}
          </div>
          <div>
            <div class="rpt-subtitle">Lead Stages</div>
            ${byStage.map(([k, v]) => `<div class="rpt-bar-row"><span class="rpt-bar-label">${k}</span><span class="rpt-bar-track"><span class="rpt-bar-fill" style="width:${(v/Math.max(...byStage.map(x=>x[1])))*100}%;background:var(--accent)"></span></span><span class="rpt-bar-val">${v}</span></div>`).join('')}
          </div>
        </div>
        <div class="report-analysis">
          <p>Geographic concentration: <b>${hubCount} leads (${pct(hubCount, a.totals.leads)})</b> are in major biotech hubs${topState ? `, led by <b>${topState[0]} (${topState[1]})</b>` : ''}.
          ${byStage.find(([k]) => k.includes('Phase 1')) ? `Early-stage (Phase 1) trials represent a key opportunity for preclinical CRO services.` : ''}
          ${byStage.find(([k]) => k.includes('Phase 2')) ? ` Phase 2 programs indicate active clinical development pipelines requiring bioanalytical and DMPK support.` : ''}</p>
        </div>
        ${topLeadsList ? `<div class="rpt-subtitle" style="margin-top:12px">Top Leads</div>${topLeadsList}` : ''}
        ${byFocus.length ? `<div class="rpt-subtitle" style="margin-top:12px">Therapeutic Focus Areas</div>${byFocus.slice(0, 8).map(([k, v]) => hl('🔬', `${k}`, `${v} leads`)).join('')}` : ''}`;
    }

    // ── 3. SERVICE DEMAND ────────────────────────────────────────────
    let svcHTML = '';
    if (a?.service_demand) {
      const svc = Object.entries(a.service_demand);
      const maxSvc = Math.max(...svc.map(x => x[1]));
      const top3 = svc.slice(0, 3).map(x => x[0]).join(', ');
      svcHTML = `
        ${svc.map(([k, v]) => `<div class="rpt-bar-row"><span class="rpt-bar-label">${k}</span><span class="rpt-bar-track"><span class="rpt-bar-fill" style="width:${(v/maxSvc)*100}%;background:var(--green)"></span></span><span class="rpt-bar-val">${v}</span></div>`).join('')}
        <div class="report-analysis">
          <p>The top 3 services in demand are <b>${top3}</b>. These align with Medicilon's core capabilities.
          ${svc.find(([k]) => k.includes('DMPK')) ? `DMPK leads with ${svc.find(([k]) => k.includes('DMPK'))[1]} requests — this is the primary outsourcing driver across all therapeutic areas.` : ''}
          ${svc.find(([k]) => k.includes('Bioanalysis')) ? ` Bioanalysis is the second-highest demand category, indicating strong need for LC-MS/MS and immunochemistry support.` : ''}
          ${svc.find(([k]) => k.includes('Toxicology')) ? ` Toxicology demand suggests clients are advancing into IND-enabling studies.` : ''}</p>
        </div>`;
    }

    // ── 4. DEALS & M&A ──────────────────────────────────────────────
    let dealsHTML = '';
    if (deals?.deals) {
      const dl = deals.deals;
      const byType = {};
      dl.forEach(d => { const t = d.deal_type || 'Other'; byType[t] = (byType[t] || 0) + 1; });
      const typeSummary = Object.entries(byType).map(([k, v]) => `${k} (${v})`).join(' · ');
      dealsHTML = `
        <div class="rpt-subtitle">Deal Breakdown: ${typeSummary}</div>
        ${dl.map(d => {
          const amt = d.amount ? ` · <b style="color:var(--accent)">${d.amount}</b>` : '';
          return hl('💼', `${d.target}${amt}`, `${d.deal_type} · ${d.date} · ${(d.description || '').substring(0, 150)}`);
        }).join('')}
        <div class="report-analysis">
          <p>${dl.length} deals tracked. ${dl.filter(d => d.deal_type === 'Funding').length} funding rounds indicate active capital flow in the biotech sector.
          ${dl.find(d => d.deal_type === 'M&A') ? 'M&A activity signals consolidation — potential for new CRO partnerships as merged entities rationalize vendor lists.' : ''}
          ${dl.find(d => d.deal_type === 'IPO') ? 'IPO activity suggests mature biotechs entering public markets, which typically accelerates outsourcing.' : ''}</p>
        </div>`;
    }

    // ── 5. NEWS INTELLIGENCE ─────────────────────────────────────────
    let newsHTML = '';
    if (news?.articles) {
      const articles = news.articles;
      const bySource = {};
      articles.forEach(a => { const s = a.source || 'Other'; bySource[s] = (bySource[s] || 0) + 1; });

      // Group by source for analysis
      const endpointsArticles = articles.filter(a => a.source === 'Endpoints News');
      const fierceArticles = articles.filter(a => a.source?.includes('Fierce'));
      const googleArticles = articles.filter(a => a.source?.includes('Google'));

      newsHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
          ${Object.entries(bySource).slice(0, 6).map(([k, v]) => `<div class="report-stat" style="padding:10px"><div class="stat-value" style="font-size:18px">${v}</div><div class="stat-label" style="font-size:9px">${k.replace('Google News - ', '')}</div></div>`).join('')}
        </div>
        ${articles.slice(0, 8).map(a => hl('📰', a.title, `${a.source} · ${a.date} · ${(a.summary || '').substring(0, 130)}`)).join('')}
        <div class="report-analysis">
          <p>${articles.length} articles from ${Object.keys(bySource).length} sources.
          ${endpointsArticles.length ? `<b>Endpoints News</b> contributed ${endpointsArticles.length} articles — key industry publication for competitive intelligence.` : ''}
          ${googleArticles.length ? ` ${googleArticles.length} articles from Google News monitoring cover competitor mentions and market movements.` : ''}
          Key themes: CRO manufacturing partnerships, clinical trial milestones, and regulatory developments.</p>
        </div>`;
    }

    // ── 6. LINKEDIN SIGNALS ──────────────────────────────────────────
    let linkedinHTML = '';
    if (a?.linkedin) {
      const kw = Object.entries(a.linkedin.top_keywords || {});
      const comp = Object.entries(a.linkedin.top_companies || {});
      const titles = Object.entries(a.linkedin.contact_titles || {});
      linkedinHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
          <div>
            <div class="rpt-subtitle">Trending Keywords</div>
            ${kw.length ? kw.map(([k, v]) => `<div class="rpt-bar-row"><span class="rpt-bar-label">${k}</span><span class="rpt-bar-track"><span class="rpt-bar-fill" style="width:${(v/Math.max(...kw.map(x=>x[1])))*100}%;background:var(--gold)"></span></span><span class="rpt-bar-val">${v}</span></div>`).join('') : '<div style="color:var(--text-dim);font-size:12px">No keyword data yet</div>'}
          </div>
          <div>
            <div class="rpt-subtitle">Decision-Maker Titles</div>
            ${titles.length ? titles.map(([k, v]) => `<div class="rpt-bar-row"><span class="rpt-bar-label">${k}</span><span class="rpt-bar-track"><span class="rpt-bar-fill" style="width:${(v/Math.max(...titles.map(x=>x[1])))*100}%;background:var(--purple)"></span></span><span class="rpt-bar-val">${v}</span></div>`).join('') : '<div style="color:var(--text-dim);font-size:12px">No contact data yet</div>'}
          </div>
        </div>
        ${comp.length ? `<div class="rpt-subtitle" style="margin-top:12px">Top Companies Mentioned</div><div>${tags(comp.slice(0, 8), 'rpt-tag-amber')}</div>` : ''}
        <div class="report-analysis">
          <p>${a.totals.linkedin_posts} LinkedIn signals analyzed.
          ${kw.length ? `Top keywords <b>${kw.slice(0,3).map(x=>x[0]).join(', ')}</b> indicate active BD conversations in the biotech ecosystem.` : ''}
          ${titles.find(([k]) => k.includes('VP')) ? ` VP/C-suite presence suggests senior decision-makers are active on the platform.` : ''}</p>
        </div>`;
    }

    // ── 7. COMPETITIVE LANDSCAPE ─────────────────────────────────────
    let compHTML = '';
    if (cros?.cros) {
      const topCros = cros.cros.slice(0, 5);
      const svcCats = cros.service_categories || [];
      compHTML = `
        <div class="rpt-subtitle">Key Competitors (Top 5)</div>
        ${topCros.map(c => hl('🏢', c.name || c.organization, `${c.location || ''} · ${(c.services || []).slice(0, 3).join(', ')}${c.headcount ? ' · ~' + c.headcount + ' employees' : ''}`)).join('')}
        ${svcCats.length ? `<div class="rpt-subtitle" style="margin-top:12px">Service Categories Tracked</div><div>${svcCats.slice(0, 10).map(s => `<span class="rpt-tag">${s}</span>`).join('')}</div>` : ''}
        <div class="report-analysis">
          <p>The CRO competitive landscape includes ${cros.cros?.length || 'multiple'} tracked organizations.
          Key differentiators for Medicilon: integrated DMPK + bioanalysis + toxicology under one roof, competitive China-based pricing, and rapid turnaround for IND-enabling packages.</p>
        </div>`;
    }

    // ── 8. RECOMMENDATIONS ───────────────────────────────────────────
    const recs = [];
    if (a) {
      recs.push({ priority: 'high', text: `Review ${a.totals.leads} active intelligence leads — prioritize Phase 1 and Phase 2 trials in top biotech hubs (CA, MA)` });
      if (a.totals.deals > 0) recs.push({ priority: 'high', text: `Monitor ${a.totals.deals} active deals for newly funded companies seeking CRO partners after capital raises` });
      if (a.totals.linkedin_posts > 0) recs.push({ priority: 'medium', text: `Engage with ${a.totals.linkedin_posts} LinkedIn signals — follow companies and decision-makers showing active BD intent` });
      recs.push({ priority: 'medium', text: 'DMPK and Bioanalysis are the top service demands — prepare capability decks and case studies for these areas' });
      recs.push({ priority: 'medium', text: 'Track toxicology demand trends — high toxicology requests indicate clients are entering IND-enabling phases' });
      recs.push({ priority: 'low', text: 'Set up Google News alerts for top competitors to stay ahead of partnership announcements' });
      recs.push({ priority: 'low', text: 'Schedule weekly review of clinical trial registrations for new Phase 1 starts in oncology and immunology' });
    }

    // ── ASSEMBLE REPORT ──────────────────────────────────────────────
    const modal = overlay.querySelector('.report-modal');
    modal.innerHTML = `
      <div class="report-header">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
          <div>
            <h2 style="margin:0;font-size:22px;font-weight:700;letter-spacing:-0.02em">📋 Daily Intelligence Report</h2>
            <div style="font-size:12px;color:var(--text-dim);margin-top:4px">${dateStr} · Generated at ${timeStr} · CONFIDENTIAL</div>
          </div>
          <div style="display:flex;gap:8px">
            <button class="btn btn-sm btn-primary" onclick="window.print()">🖨️ Print</button>
            <button class="btn btn-sm" onclick="document.getElementById('report-overlay').remove()">✕ Close</button>
          </div>
        </div>
        <div style="height:1px;background:var(--border-soft);margin-top:20px"></div>
      </div>
      <div class="report-body">

        <!-- 1. EXECUTIVE SUMMARY -->
        <div class="report-section">
          <div class="rpt-section-num">01</div>
          <h3>📊 Executive Summary</h3>
          ${summaryHTML || '<div class="report-analysis"><p>Analytics data unavailable. Ensure the backend is running at http://localhost:8000.</p></div>'}
        </div>

        <!-- 2. LEAD INTELLIGENCE -->
        <div class="report-section">
          <div class="rpt-section-num">02</div>
          <h3>🎯 Lead Intelligence</h3>
          ${leadsHTML || '<div class="report-analysis"><p>No lead data available.</p></div>'}
        </div>

        <!-- 3. SERVICE DEMAND -->
        <div class="report-section">
          <div class="rpt-section-num">03</div>
          <h3>💊 CRO Service Demand Analysis</h3>
          ${svcHTML || '<div class="report-analysis"><p>No service demand data available.</p></div>'}
        </div>

        <!-- 4. DEALS & M&A -->
        <div class="report-section">
          <div class="rpt-section-num">04</div>
          <h3>💼 Deals & M&A Activity</h3>
          ${dealsHTML || '<div class="report-analysis"><p>No deal data available.</p></div>'}
        </div>

        <!-- 5. NEWS INTELLIGENCE -->
        <div class="report-section">
          <div class="rpt-section-num">05</div>
          <h3>📰 News Intelligence</h3>
          ${newsHTML || '<div class="report-analysis"><p>No news data available.</p></div>'}
        </div>

        <!-- 6. LINKEDIN SIGNALS -->
        <div class="report-section">
          <div class="rpt-section-num">06</div>
          <h3>🔗 LinkedIn Signal Intelligence</h3>
          ${linkedinHTML || '<div class="report-analysis"><p>No LinkedIn data available. Run the aggregator to populate signals.</p></div>'}
        </div>

        <!-- 7. COMPETITIVE LANDSCAPE -->
        <div class="report-section">
          <div class="rpt-section-num">07</div>
          <h3>🏢 Competitive Landscape</h3>
          ${compHTML || '<div class="report-analysis"><p>CRO competitive data unavailable.</p></div>'}
        </div>

        <!-- 8. RECOMMENDATIONS -->
        <div class="report-section" style="border-left:3px solid var(--primary);background:rgba(99,102,241,0.03)">
          <div class="rpt-section-num" style="background:var(--primary);color:white">08</div>
          <h3>💡 Recommended Actions</h3>
          ${recs.map((r, i) => `<div class="report-highlight" style="border-left-color:${r.priority === 'high' ? 'var(--red)' : r.priority === 'medium' ? 'var(--gold)' : 'var(--text-dim)'}">
            <span style="display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;background:${r.priority === 'high' ? 'rgba(239,68,68,0.15)' : r.priority === 'medium' ? 'rgba(251,191,36,0.15)' : 'rgba(113,113,122,0.15)'};border-radius:50%;font-size:10px;font-weight:700;margin-right:6px;color:${r.priority === 'high' ? 'var(--red)' : r.priority === 'medium' ? 'var(--gold)' : 'var(--text-dim)'}">${i + 1}</span>
            ${r.text}
          </div>`).join('')}
        </div>

        <div style="text-align:center;padding:16px;font-size:10px;color:var(--text-dim);border-top:1px solid var(--border-dim);margin-top:12px">
          Generated by Medicilon CRO Intelligence Platform v0.3.0 · For internal use only · ${dateStr}
        </div>
      </div>
    `;
  },
};
