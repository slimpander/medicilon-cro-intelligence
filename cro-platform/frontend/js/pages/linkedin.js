/**
 * LinkedIn Intelligence Page — Automated BD Signal Monitor
 * No extension needed. Pulls from multi-source aggregator + optional Chrome extension data.
 * One-click "Aggregate Now" runs server-side RSS/SEC scraping.
 */
const PageLinkedIn = {
  posts: [],           // DB posts (aggregator + extension)
  aggregated: [],      // Latest aggregation run (from JSON)
  contacts: [],
  stats: {},
  filters: { minScore: 0, keyword: '', tier: '' },
  aggregating: false,

  async render(container) {
    container.innerHTML = `
      <div class="page-header flex-between">
        <div>
          <div class="page-title">🌿 BD Intelligence Feed</div>
          <div class="page-subtitle">Automated signal detection — no LinkedIn account required</div>
        </div>
        <div class="flex-center gap-8">
          <span id="aggregate-status" style="font-size:11px;color:var(--text-dim)"></span>
          <button class="btn btn-primary btn-sm" id="linkedin-aggregate-btn" style="gap:6px">
            <span id="aggregate-btn-icon">🔄</span> Aggregate Now
          </button>
          <button class="btn btn-sm" id="linkedin-refresh-btn">↻ Refresh</button>
        </div>
      </div>

      <!-- Stats Row -->
      <div class="kpi-grid mb-16" id="linkedin-kpis">
        <div class="kpi-card"><div class="kpi-label">Total Signals</div><div class="kpi-value" id="kpi-posts">—</div><div class="kpi-change up" id="kpi-aggregated-badge" style="display:none">aggregated</div></div>
        <div class="kpi-card"><div class="kpi-label">Tier S / A</div><div class="kpi-value" id="kpi-priority">—</div></div>
        <div class="kpi-card"><div class="kpi-label">Decision Makers</div><div class="kpi-value" id="kpi-contacts">—</div></div>
        <div class="kpi-card"><div class="kpi-label">Data Sources</div><div class="kpi-value" id="kpi-sources">—</div></div>
      </div>

      <!-- Filter Bar -->
      <div class="filter-bar mb-16">
        <input type="text" class="form-input" placeholder="Filter by keyword..." id="linkedin-filter-keyword" style="max-width:220px">
        <select class="form-input" id="linkedin-filter-score" style="max-width:160px">
          <option value="0">All Tiers</option>
          <option value="S">Tier S (70+)</option>
          <option value="A">Tier A (50-69)</option>
          <option value="B">Tier B (30-49)</option>
          <option value="C">Tier C (10-29)</option>
        </select>
        <span class="filter-spacer"></span>
        <button class="btn btn-sm" id="linkedin-clear-btn">Clear</button>
        <span style="font-size:11px;color:var(--text-dim)" id="linkedin-count"></span>
      </div>

      <!-- Two Column: Signals + Contacts -->
      <div class="grid-2col mb-24" style="align-items:start">
        <!-- Signals Column -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">📡 BD Signals</div>
            <div class="flex-center gap-6">
              <span id="auto-source-badge" class="tag tag-green" style="font-size:9px;display:none">Auto</span>
              <span id="linkedin-post-count" class="tag tag-default">0</span>
            </div>
          </div>
          <div id="linkedin-posts-list" style="max-height:520px;overflow-y:auto">
            <div class="empty-state">
              <div class="empty-state-icon">🌱</div>
              <div class="empty-state-title">No signals yet</div>
              <div class="empty-state-desc">Click "Aggregate Now" to scan public sources for BD intelligence</div>
            </div>
          </div>
        </div>

        <!-- Contacts + Sources Column -->
        <div style="display:flex;flex-direction:column;gap:14px">
          <div class="card">
            <div class="card-header">
              <div class="card-title">👤 Decision Makers</div>
              <span id="linkedin-contact-count" class="tag tag-gold">0</span>
            </div>
            <div id="linkedin-contacts-list" style="max-height:240px;overflow-y:auto">
              <div class="empty-state">
                <div class="empty-state-desc">Detected from company announcements</div>
              </div>
            </div>
          </div>

          <div class="card">
            <div class="card-header">
              <div class="card-title">📋 Data Sources</div>
            </div>
            <div id="linkedin-sources-info" style="font-size:11px;color:var(--text-soft);line-height:1.7;padding:4px 0">
              <div class="empty-state-desc">Run aggregation to populate</div>
            </div>
          </div>
        </div>
      </div>

      <!-- How it Works -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">🔄 How It Works</div>
        </div>
        <div style="padding:8px 0;font-size:12px;color:var(--text-soft);line-height:1.8">
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px">
            <div style="padding:12px;background:var(--surface2);border-radius:var(--radius-sm)">
              <strong style="color:var(--moss)">📰 Google News</strong>
              <div style="font-size:11px;color:var(--text-dim);margin-top:4px">Biotech funding, CRO partnerships, hiring announcements</div>
            </div>
            <div style="padding:12px;background:var(--surface2);border-radius:var(--radius-sm)">
              <strong style="color:var(--moss)">📡 Industry RSS</strong>
              <div style="font-size:11px;color:var(--text-dim);margin-top:4px">FierceBiotech, Endpoints, BioPharma Dive</div>
            </div>
            <div style="padding:12px;background:var(--surface2);border-radius:var(--radius-sm)">
              <strong style="color:var(--moss)">📋 PR Newswire</strong>
              <div style="font-size:11px;color:var(--text-dim);margin-top:4px">Official biotech press releases</div>
            </div>
            <div style="padding:12px;background:var(--surface2);border-radius:var(--radius-sm)">
              <strong style="color:var(--moss)">💰 SEC EDGAR</strong>
              <div style="font-size:11px;color:var(--text-dim);margin-top:4px">Form D filings — funding round signals</div>
            </div>
          </div>
          <div style="margin-top:12px;padding:10px;background:var(--surface2);border-radius:var(--radius-sm);font-size:11px">
            <strong>Also supports:</strong> Chrome extension data — posts from the extension merge into the same feed automatically
          </div>
        </div>
      </div>
    `;

    await this.loadData();
    this.renderAll();
    this.setupListeners();
    this.checkAutoStatus();
  },

  async loadData() {
    try {
      const [postsR, contactsR, statsR, aggR] = await Promise.allSettled([
        fetch(`${App.apiBase}/linkedin/posts?limit=80`),
        fetch(`${App.apiBase}/linkedin/contacts`),
        fetch(`${App.apiBase}/linkedin/stats`),
        fetch(`${App.apiBase}/linkedin/aggregated?limit=80`),
      ]);

      if (postsR.status === 'fulfilled' && postsR.value.ok) {
        this.posts = await postsR.value.json();
      }
      if (contactsR.status === 'fulfilled' && contactsR.value.ok) {
        this.contacts = await contactsR.value.json();
      }
      if (statsR.status === 'fulfilled' && statsR.value.ok) {
        this.stats = await statsR.value.json();
      }
      if (aggR.status === 'fulfilled' && aggR.value.ok) {
        const aggData = await aggR.value.json();
        this.aggregated = aggData.leads || [];
        this.aggGenerated = aggData.generated;
      }
    } catch (e) {
      console.log('[LinkedIn] Backend unavailable — showing demo mode');
      this._loadDemoData();
    }
  },

  _loadDemoData() {
    this.stats = { total_posts: 4, total_contacts: 2, avg_relevance: 65, high_priority: 2 };
    this.posts = [
      { id: 1, author_name: 'NeuroBio Therapeutics', author_title: 'VP R&D', author_company: 'NeuroBio Therapeutics',
        content: '[Google News] Seeking CRO partners for preclinical DMPK program — comprehensive ADME profiling and tox screening for lead candidate.',
        post_date: '2026-05-24', relevance_score: 92, matched_keywords: 'DMPK, ADME, preclinical, CRO, toxicology, outsourcing' },
      { id: 2, author_name: 'GenTech Biosciences', author_title: 'Head of Preclinical', author_company: 'GenTech Biosciences',
        content: '[PR Newswire] Just closed Series B! Building preclinical team. Looking for CROs in bioanalysis and IND-enabling studies.',
        post_date: '2026-05-23', relevance_score: 88, matched_keywords: 'Series B, preclinical, CRO, bioanalysis, IND' },
      { id: 3, author_name: 'NovaCell Therapeutics', author_title: 'CSO', author_company: 'NovaCell Therapeutics',
        content: '[BioPharma Dive] IND accepted for NCL-001. Scaling CMC and tox for Phase 1.',
        post_date: '2026-05-21', relevance_score: 75, matched_keywords: 'IND, CMC, tox, Phase 1, drug development' },
      { id: 4, author_name: 'BioPharm Solutions', author_title: 'Director of Toxicology', author_company: 'BioPharm Solutions',
        content: '[FierceBiotech] Strategic CRO partnerships for complex biologics programs — BIO panel discussion.',
        post_date: '2026-05-22', relevance_score: 62, matched_keywords: 'outsourcing, CRO, biologics, toxicology' },
    ];
    this.contacts = [
      { name: 'NeuroBio Therapeutics', title: 'VP R&D', company: 'NeuroBio Therapeutics', relevance_score: 9.2 },
      { name: 'NovaCell Therapeutics', title: 'CSO', company: 'NovaCell Therapeutics', relevance_score: 7.5 },
    ];
  },

  renderAll() {
    this.renderKPIs();
    this.renderPosts();
    this.renderContacts();
    this.renderSources();
  },

  renderKPIs() {
    const totalPosts = this.stats.total_posts || this.posts.length || 0;
    const highPriority = this.stats.high_priority || 0;
    const totalContacts = this.stats.total_contacts || this.contacts.length || 0;

    document.getElementById('kpi-posts').textContent = totalPosts || '—';
    document.getElementById('kpi-priority').textContent = highPriority || '—';
    document.getElementById('kpi-contacts').textContent = totalContacts || '—';

    // Count unique sources from posts
    const sources = new Set();
    for (const p of this.posts) {
      const src = this._extractSource(p);
      if (src) sources.add(src);
    }
    document.getElementById('kpi-sources').textContent = sources.size || '—';

    // Show aggregated badge if we have aggregator data
    const badge = document.getElementById('kpi-aggregated-badge');
    if (badge && this.aggregated.length > 0) {
      badge.style.display = '';
      badge.textContent = `${this.aggregated.length} from RSS`;
    }
  },

  _extractSource(post) {
    // Try to extract source from content prefix like "[Google News]"
    const content = post.content || '';
    const match = content.match(/^\[(.+?)\]/);
    if (match) return match[1];
    // Or from author_company if it looks like a news source
    const author = post.author_company || post.author_name || '';
    if (/(News|Times|Journal|Wire|PR|RSS|SEC|EDGAR|Fierce|Endpoints|BioPharma)/i.test(author)) return author;
    return 'LinkedIn';
  },

  _getTier(score) {
    if (score >= 70) return { label: 'S', color: 'var(--leaf)', bg: 'rgba(61,110,68,0.1)' };
    if (score >= 50) return { label: 'A', color: 'var(--moss)', bg: 'rgba(61,100,68,0.08)' };
    if (score >= 30) return { label: 'B', color: 'var(--gold)', bg: 'rgba(122,106,58,0.1)' };
    if (score >= 10) return { label: 'C', color: 'var(--text-dim)', bg: 'rgba(0,0,0,0.04)' };
    return { label: 'D', color: 'var(--text-dim)', bg: 'rgba(0,0,0,0.03)' };
  },

  renderPosts() {
    const el = document.getElementById('linkedin-posts-list');
    const countEl = document.getElementById('linkedin-post-count');
    if (!el) return;

    // Merge posts + aggregated leads
    const allSignals = [...this.posts];
    for (const lead of this.aggregated) {
      // Avoid duplicates by title
      const exists = allSignals.some(p =>
        (p.content || '').includes((lead.title || '').slice(0, 60))
      );
      if (!exists) {
        allSignals.push({
          id: 'agg-' + lead.title?.slice(0, 30),
          author_name: lead.author_company || lead.source || 'Industry Signal',
          author_title: lead.author_title || '',
          author_company: lead.author_company || '',
          content: lead.content || `[${lead.source}] ${lead.title}`,
          post_date: lead.date || '',
          relevance_score: lead.relevance_score || 0,
          matched_keywords: lead.matched_keywords || '',
          post_url: lead.url || '',
          _tier: lead.tier,
          _source: lead.source,
          _is_aggregated: true,
          _title: lead.title || '',
        });
      }
    }

    // Apply filters
    let filtered = allSignals;
    if (this.filters.tier) {
      filtered = filtered.filter(p => {
        const tier = p._tier || this._getTier(p.relevance_score || 0).label;
        return tier === this.filters.tier;
      });
    }
    if (this.filters.minScore > 0) {
      filtered = filtered.filter(p => (p.relevance_score || 0) >= this.filters.minScore);
    }
    if (this.filters.keyword) {
      const kw = this.filters.keyword.toLowerCase();
      filtered = filtered.filter(p =>
        (p.matched_keywords || '').toLowerCase().includes(kw) ||
        (p.content || '').toLowerCase().includes(kw) ||
        (p.author_name || '').toLowerCase().includes(kw) ||
        (p.author_company || '').toLowerCase().includes(kw)
      );
    }
    filtered.sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));

    if (countEl) countEl.textContent = filtered.length;
    const countSpan = document.getElementById('linkedin-count');
    if (countSpan) countSpan.textContent = `${filtered.length} signals (${allSignals.length} total)`;

    if (!filtered.length) {
      el.innerHTML = `<div class="empty-state" style="padding:32px 20px">
        <div class="empty-state-icon">🌱</div>
        <div class="empty-state-title">${allSignals.length ? 'No signals match filters' : 'No signals yet'}</div>
        <div class="empty-state-desc">${allSignals.length ? 'Try adjusting filters' : 'Click "Aggregate Now" to scan public sources'}</div>
      </div>`;
      return;
    }

    el.innerHTML = filtered.map(p => {
      const score = p.relevance_score || 0;
      const tier = p._tier || this._getTier(score).label;
      const src = p._source || this._extractSource(p);
      const isAgg = p._is_aggregated;
      const keywords = (p.matched_keywords || '').split(',').map(k => k.trim()).filter(Boolean);
      const date = p.post_date ? App.relativeDate(p.post_date) : '';
      const author = p.author_name || 'Unknown';
      const title = p.author_title || '';
      const company = p.author_company || '';
      const url = p.post_url || p._url || '';
      // Extract clean headline: strip [Source] prefix, use first sentence
      const headline = p._title ||
        (p.content || '').replace(/^\[.*?\]\s*/, '').split('\n')[0].slice(0, 120);

      // Tier styling
      const tierColors = { S: 'var(--leaf)', A: 'var(--moss)', B: 'var(--gold)', C: 'var(--text-dim)', D: 'var(--text-dim)' };
      const tierColor = tierColors[tier] || 'var(--text-dim)';

      return `
        <div style="padding:12px;border-bottom:1px solid var(--border-soft);
          ${tier === 'S' || tier === 'A' ? 'border-left:3px solid ' + tierColor + ';' : ''}
          ${url ? 'cursor:pointer;' : ''}transition:background var(--transition)"
          class="dash-news-item"
          ${url ? `onclick="window.open('${url.replace(/'/g, "&#39;")}', '_blank')" title="Open source article"` : ''}>
          <div class="flex-between mb-6">
            <div class="flex-center gap-8">
              <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;font-size:9px;font-weight:700;background:${tierColor}18;color:${tierColor}">${tier}</span>
              <strong style="font-size:12px">${author.slice(0, 35)}</strong>
              ${isAgg ? '<span class="tag tag-green" style="font-size:8px;padding:1px 6px">auto</span>' : ''}
            </div>
            <div class="flex-center gap-6">
              <span style="font-size:9px;color:var(--text-dim);background:var(--surface2);padding:2px 6px;border-radius:4px">${src}</span>
              <span style="font-size:10px;color:var(--text-dim)">${date}</span>
              ${url ? `<a href="${url}" target="_blank" onclick="event.stopPropagation()"
                style="font-size:11px;color:var(--accent);text-decoration:none;opacity:.7;transition:opacity .15s"
                onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=.7"
                title="Open source article">↗</a>` : ''}
            </div>
          </div>
          ${headline ? `<div style="font-size:12px;font-weight:600;color:var(--text);line-height:1.4;margin-bottom:5px">${headline}</div>` : ''}
          ${title ? `<div style="font-size:10px;color:var(--moss);margin-bottom:4px;font-weight:500">${title}</div>` : ''}
          ${company && company !== author ? `<div style="font-size:10px;color:var(--text-soft);margin-bottom:4px">${company}</div>` : ''}
          <div style="font-size:11px;color:var(--text-soft);line-height:1.5;margin-bottom:6px">
            ${(p.content || '').replace(/^\[.+?\]\s*/, '').replace(headline, '').trim().slice(0, 200)}${(p.content || '').length > 250 ? '...' : ''}
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:3px;align-items:center">
            ${keywords.slice(0, 6).map(k => `<span class="tag tag-default" style="font-size:9px;padding:2px 6px">${k}</span>`).join('')}
            ${keywords.length > 6 ? `<span class="tag tag-default" style="font-size:9px">+${keywords.length - 6}</span>` : ''}
            ${url ? `<a href="${url}" target="_blank" onclick="event.stopPropagation()"
              style="margin-left:auto;font-size:10px;color:var(--accent);text-decoration:none;display:flex;align-items:center;gap:3px;padding:2px 8px;border-radius:4px;border:1px solid rgba(0,212,255,.25);background:rgba(0,212,255,.06)">Open source ↗</a>` : ''}
          </div>
          ${tier === 'S' ? '<div style="font-size:10px;color:var(--leaf);margin-top:6px">🔥 High priority — direct CRO opportunity signal</div>' : ''}
        </div>
      `;
    }).join('');
  },

  renderContacts() {
    const el = document.getElementById('linkedin-contacts-list');
    const countEl = document.getElementById('linkedin-contact-count');
    if (!el) return;

    if (countEl) countEl.textContent = this.contacts.length;

    if (!this.contacts.length) {
      el.innerHTML = `<div class="empty-state" style="padding:16px">
        <div class="empty-state-desc">Decision-makers detected from company announcements and post content</div>
      </div>`;
      return;
    }

    el.innerHTML = this.contacts.slice(0, 12).map(c => `
      <div style="padding:10px;border-bottom:1px solid var(--border-soft);transition:background var(--transition)" class="dash-news-item">
        <div class="flex-between mb-4">
          <strong style="font-size:12px">${c.name || 'Unknown'}</strong>
          <span class="tag tag-gold" style="font-size:9px">${c.relevance_score || '—'}</span>
        </div>
        <div style="font-size:10px;color:var(--moss);margin-bottom:2px">${c.title || ''}</div>
        <div style="font-size:10px;color:var(--text-soft)">${c.company || ''}</div>
        ${c.company_state ? `<div style="font-size:9px;color:var(--text-dim);margin-top:2px">📍 ${c.company_state}</div>` : ''}
      </div>
    `).join('');
  },

  renderSources() {
    const el = document.getElementById('linkedin-sources-info');
    if (!el) return;

    const sourceCounts = {};
    for (const p of [...this.posts, ...this.aggregated.map(l => ({ content: `[${l.source}]`, _source: l.source }))]) {
      const src = p._source || this._extractSource(p);
      if (src) sourceCounts[src] = (sourceCounts[src] || 0) + 1;
    }

    if (Object.keys(sourceCounts).length === 0) {
      el.innerHTML = '<div class="empty-state-desc">No data sources yet</div>';
      return;
    }

    el.innerHTML = Object.entries(sourceCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([src, count]) => `
        <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border-soft)">
          <span>${src}</span>
          <span class="tag tag-default" style="font-size:9px">${count}</span>
        </div>
      `).join('');
  },

  async checkAutoStatus() {
    const el = document.getElementById('aggregate-status');
    if (!el) return;
    if (this.aggregated.length > 0) {
      const gen = this.aggGenerated ? new Date(this.aggGenerated) : null;
      const label = gen ? App.relativeDate(gen.toISOString()) : 'recently';
      el.textContent = `Last aggregated: ${label}`;
      el.style.color = 'var(--leaf)';
    } else {
      el.textContent = 'Not yet aggregated';
      el.style.color = 'var(--text-dim)';
    }
  },

  setupListeners() {
    // Aggregate Now
    document.getElementById('linkedin-aggregate-btn')?.addEventListener('click', async () => {
      if (this.aggregating) return;
      this.aggregating = true;
      const btn = document.getElementById('linkedin-aggregate-btn');
      const icon = document.getElementById('aggregate-btn-icon');
      const status = document.getElementById('aggregate-status');
      btn.disabled = true;
      if (icon) icon.textContent = '⏳';
      if (status) { status.textContent = 'Aggregating from public sources...'; status.style.color = 'var(--gold)'; }
      App.showToast('Aggregating BD intelligence from public sources...', 'info');

      try {
        const r = await App.apiFetch(`${App.apiBase}/linkedin/aggregate`, { method: 'POST' });
        if (r.status === 401) {
          App.showToast('Sign in to run aggregation', 'error');
          document.getElementById('login-modal-overlay').style.display = 'flex';
        } else {
          const data = await r.json();
          if (data.ok) {
            App.showToast(`${data.total_signals} new signals collected`, 'success');
            if (status) { status.textContent = 'Aggregation complete'; status.style.color = 'var(--leaf)'; }
          } else {
            App.showToast('Aggregation failed: ' + (data.error || 'unknown'), 'error');
          }
        }
      } catch (e) {
        App.showToast('Aggregation failed — is the backend running?', 'error');
        console.error('[LinkedIn] Aggregate error:', e);
      }

      this.aggregating = false;
      btn.disabled = false;
      if (icon) icon.textContent = '🔄';
      await this.loadData();
      this.renderAll();
      this.checkAutoStatus();
    });

    // Refresh
    document.getElementById('linkedin-refresh-btn')?.addEventListener('click', async () => {
      await this.loadData();
      this.renderAll();
      this.checkAutoStatus();
      App.showToast('Feed refreshed', 'success');
    });

    // Tier filter
    document.getElementById('linkedin-filter-score')?.addEventListener('change', (e) => {
      this.filters.tier = e.target.value === '0' ? '' : e.target.value;
      if (this.filters.tier === 'S') this.filters.minScore = 70;
      else if (this.filters.tier === 'A') this.filters.minScore = 50;
      else if (this.filters.tier === 'B') this.filters.minScore = 30;
      else if (this.filters.tier === 'C') this.filters.minScore = 10;
      else this.filters.minScore = 0;
      this.renderPosts();
    });

    // Keyword filter
    document.getElementById('linkedin-filter-keyword')?.addEventListener('input', (e) => {
      this.filters.keyword = e.target.value;
      this.renderPosts();
    });

    // Clear filters
    document.getElementById('linkedin-clear-btn')?.addEventListener('click', () => {
      this.filters = { minScore: 0, keyword: '', tier: '' };
      ['linkedin-filter-keyword', 'linkedin-filter-score'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '0';
      });
      this.renderPosts();
    });
  },
};
