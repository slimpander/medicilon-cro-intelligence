/**
 * News Feed Page — CRO industry news with search and filtering
 */
const PageNews = {
  filters: { company: '', search: '', date: '' },

  render(container) {
    const newsData = App.newsData;
    const articles = newsData?.articles || [];

    container.innerHTML = `
      <div class="page-header flex-between">
        <div>
          <div class="page-title">News Feed</div>
          <div class="page-subtitle">
            ${newsData ? `${articles.length} articles · Past ${newsData.metadata?.lookback_years || 3} years` : 'News feed not loaded'}
          </div>
        </div>
        <button class="btn btn-sm" id="news-refresh-btn">🔄 Refresh</button>
      </div>

      <!-- Search + Filter -->
      <div class="filter-bar">
        <input type="text" id="news-search-input" placeholder="Search articles..." style="flex:1;max-width:300px">
        <select id="news-company-filter">
          <option value="">All Companies</option>
          ${[...new Set(articles.flatMap(a => a.tags || []).filter(t => t.length > 3 && t[0] === t[0].toUpperCase()))].sort().map(c => `<option>${c}</option>`).join('')}
        </select>
        <select id="news-date-filter">
          <option value="">All Time</option>
          <option value="recent">Recent (&lt;1 month)</option>
          <option value="old">Older</option>
        </select>
        <span class="filter-spacer"></span>
        <span style="font-size:11px;color:var(--text-dim)" id="news-count"></span>
      </div>

      <!-- Articles List -->
      <div id="news-list" style="display:flex;flex-direction:column;gap:8px">
        <div class="empty-state"><div class="empty-state-desc">Loading articles...</div></div>
      </div>
    `;

    this.setupFilters();
    this.renderArticles();
  },

  setupFilters() {
    document.getElementById('news-search-input')?.addEventListener('input', (e) => {
      this.filters.search = e.target.value.toLowerCase();
      this.renderArticles();
    });
    document.getElementById('news-company-filter')?.addEventListener('change', (e) => {
      this.filters.company = e.target.value;
      this.renderArticles();
    });
    document.getElementById('news-date-filter')?.addEventListener('change', (e) => {
      this.filters.date = e.target.value;
      this.renderArticles();
    });
    document.getElementById('news-refresh-btn')?.addEventListener('click', async () => {
      App.showToast('Refreshing news...', 'info');
      await App.loadData();
      this.renderArticles();
      App.showToast('News refreshed', 'success');
    });
  },

  renderArticles() {
    const list = document.getElementById('news-list');
    const countEl = document.getElementById('news-count');
    if (!list) return;

    let articles = App.newsData?.articles || [];
    if (!articles.length) {
      list.innerHTML = `<div class="empty-state">
        <div class="empty-state-icon">📰</div>
        <div class="empty-state-title">No news articles loaded</div>
        <div class="empty-state-desc">Run fetch_news.py to pull live news data</div>
      </div>`;
      return;
    }

    // Apply filters
    let filtered = articles.filter(a => {
      if (this.filters.search) {
        const text = ((a.title || '') + ' ' + (a.summary || '') + ' ' + (a.tags || []).join(' ')).toLowerCase();
        if (!text.includes(this.filters.search)) return false;
      }
      if (this.filters.company) {
        if (!(a.tags || []).includes(this.filters.company)) return false;
      }
      if (this.filters.date === 'recent') {
        if (!a.date_iso) return false;
        return (Date.now() - new Date(a.date_iso)) < 30 * 86400000;
      }
      if (this.filters.date === 'old') {
        if (!a.date_iso) return true;
        return (Date.now() - new Date(a.date_iso)) >= 30 * 86400000;
      }
      return true;
    });

    // Sort by date
    filtered.sort((a, b) => new Date(b.date_iso || 0) - new Date(a.date_iso || 0));

    if (countEl) countEl.textContent = `${filtered.length} articles`;

    list.innerHTML = filtered.length ? filtered.map(a => {
      const tags = (a.tags || []).slice(0, 4).map(t => {
        // Check if it's a service tag
        const sc = SERVICE_COLORS[t];
        if (sc) return `<span class="tag" style="background:${sc}22;border-color:${sc}44;color:${sc};font-size:9px">${t}</span>`;
        // Check if it's a state
        if (t.length === 2 && t === t.toUpperCase()) return `<span class="tag tag-default" style="font-size:9px">📍 ${t}</span>`;
        return `<span class="tag tag-default" style="font-size:9px">${t}</span>`;
      }).join('');

      return `
        <div class="card" style="cursor:pointer" ${a.url ? `onclick="window.open('${a.url.replace(/'/g, "\\'")}','_blank')"` : ''}>
          <div class="flex-between mb-6">
            <strong style="font-size:13px;line-height:1.4">${a.title || 'Untitled'}</strong>
            <span class="tag tag-default" style="font-size:9px;white-space:nowrap;margin-left:8px">${a.source || ''}</span>
          </div>
          <div class="flex-between mb-8" style="font-size:10px;color:var(--text-dim)">
            <span>${App.relativeDate(a.date_iso) || a.date || 'Unknown date'}</span>
            ${a.url ? '<span style="color:var(--accent)">Read →</span>' : ''}
          </div>
          ${a.summary ? `<div style="font-size:11px;color:var(--text-muted);line-height:1.5;margin-bottom:8px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${a.summary}</div>` : ''}
          ${tags ? `<div style="display:flex;flex-wrap:wrap;gap:3px">${tags}</div>` : ''}
        </div>
      `;
    }).join('') : `<div class="empty-state">
      <div class="empty-state-desc">No articles match current filters</div>
    </div>`;
  },
};
