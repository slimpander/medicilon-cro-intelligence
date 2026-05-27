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

      <!-- ═══ SECTION 4: CRUNCHBASE FUNDING HEADLINES ═══ -->
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
    await this.renderCrunchbase();
    await this.renderPitchBook();
    this.setupPatentSearch();
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
};
