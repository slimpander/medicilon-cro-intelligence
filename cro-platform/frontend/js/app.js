/**
 * Medicilon CRO Intelligence Platform — Application Core
 * Handles: routing, navigation, data loading, auth, notifications
 */

// ── Global State ─────────────────────────────────────────────────────────────
const App = {
  currentPage: 'dashboard',
  croData: null,
  intelligenceData: null,
  newsData: null,
  user: null,
  settings: {},
  notifications: [],
  apiBase: '/api',

  get isAdmin() {
    return this.user?.user?.role === 'admin' || this.settings?.user_role === 'admin';
  },

  async init() {
    try {
      await this.loadData();
      // Restore session from localStorage
      const savedToken = localStorage.getItem('auth_token');
      if (savedToken) {
        try {
          // Verify the token is still valid
          const r = await fetch(`${this.apiBase}/settings`, {
            headers: { 'Authorization': `Bearer ${savedToken}` }
          });
          if (r.ok) {
            this.user = { token: savedToken };
            this.settings = await r.json();
          } else {
            localStorage.removeItem('auth_token');
          }
        } catch(e) { localStorage.removeItem('auth_token'); }
      }
      this.updateAdminUI();
      this.setupNavigation();
      this.setupTopbar();
      this.navigate('dashboard');
      document.getElementById('loading-screen').style.display = 'none';
      document.getElementById('app').style.display = '';
    } catch (err) {
      console.error('App init failed:', err);
      document.getElementById('loading-screen').innerHTML =
        '<p style="color:#ff4560">Failed to load. Check console.</p>';
    }
  },

  // ── Data Loading ───────────────────────────────────────────────────────────
  async loadData() {
    const [croR, intelR, newsR] = await Promise.allSettled([
      fetch('data/cro_data.json'),
      fetch('data/intelligence.json'),
      fetch('data/news_data.json'),
    ]);

    if (croR.status === 'fulfilled' && croR.value.ok) {
      this.croData = await croR.value.json();
    } else {
      console.warn('CRO data unavailable, using embedded fallback');
      this.croData = FALLBACK_DATA;
    }

    if (intelR.status === 'fulfilled' && intelR.value.ok) {
      this.intelligenceData = await intelR.value.json();
    }
    if (newsR.status === 'fulfilled' && newsR.value.ok) {
      this.newsData = await newsR.value.json();
    }

    // Update last refresh
    const el = document.getElementById('last-refresh');
    if (el && this.croData?.metadata?.generated) {
      const d = new Date(this.croData.metadata.generated);
      el.textContent = `Data updated: ${d.toLocaleDateString('en-US', {month:'short',day:'numeric'})}`;
    }

    // Dispatch event for pages
    window.dispatchEvent(new CustomEvent('dataReady'));
  },

  // ── Navigation ─────────────────────────────────────────────────────────────
  setupNavigation() {
    // Sidebar + dropdown nav clicks — catch any element with data-nav
    document.addEventListener('click', (e) => {
      const navEl = e.target.closest('[data-nav]');
      if (!navEl) return;
      e.preventDefault();
      const page = navEl.dataset.nav;
      if (page && page !== this.currentPage) {
        this.navigate(page);
      }
    });

    // Browser back/forward
    window.addEventListener('popstate', (e) => {
      const page = e.state?.page || 'dashboard';
      this.navigate(page, false);
    });
  },

  navigate(page, pushState = true) {
    // Block non-admin access to SciLeads pages
    if (page === 'crunchbase' && !this.isAdmin) {
      this.showToast('SciLeads tools require admin access', 'error');
      return;
    }
    console.log('[Nav] navigate to:', page, 'current:', this.currentPage);
    if (this.currentPage === page && !pushState) return;

    // Update sidebar
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    const navItem = document.querySelector(`.nav-item[data-nav="${page}"]`);
    if (navItem) navItem.classList.add('active');
    else console.warn('[Nav] No nav item found for:', page);

    // Push history
    if (pushState) {
      history.pushState({ page }, '', `#${page}`);
    }

    this.currentPage = page;
    this.loadPage(page);
  },

  async loadPage(page) {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div style="text-align:center;padding:60px"><div class="loader-spinner"></div></div>';

    const renderMap = {
      dashboard:  () => PageDashboard?.render(main),
      map:        () => PageMap?.render(main),
      leads:      () => PageLeads?.render(main),
      linkedin:   () => PageLinkedIn?.render(main),
      cros:       () => PageCros?.render(main),
      pitchbook:  () => PagePitchbook?.render(main),
      crunchbase: () => PageCrunchbase?.render(main),
      news:       () => PageNews?.render(main),
      settings:   () => PageSettings?.render(main),
      analytics:  () => PageAnalytics?.render(main),
    };

    const fn = renderMap[page];
    if (!fn) {
      main.innerHTML = `<div class="empty-state">
        <div class="empty-state-icon">🚧</div>
        <div class="empty-state-title">Page not found</div>
        <div class="empty-state-desc">"${page}" is not available yet</div>
      </div>`;
      return;
    }

    try {
      fn();
    } catch (e) {
      console.error(`Error rendering page ${page}:`, e);
      main.innerHTML = `<div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Error loading page</div>
        <div class="empty-state-desc">${e.message}</div>
      </div>`;
    }
  },

  // ── Topbar ──────────────────────────────────────────────────────────────────
  setupTopbar() {
    // Notification bell
    const bell = document.getElementById('notif-bell');
    const dropdown = document.getElementById('notif-dropdown');
    bell.addEventListener('click', () => dropdown.classList.toggle('hidden'));

    // User menu
    const userBtn = document.getElementById('user-btn');
    const userDropdown = document.getElementById('user-dropdown');
    userBtn.addEventListener('click', () => {
      if (!this.user) {
        // Show login modal
        document.getElementById('login-modal-overlay').style.display = 'flex';
        return;
      }
      userDropdown.classList.toggle('hidden');
    });

    // Close dropdowns on outside click
    document.addEventListener('click', (e) => {
      if (!bell.contains(e.target) && !dropdown.contains(e.target))
        dropdown.classList.add('hidden');
      if (!userBtn.contains(e.target) && !userDropdown.contains(e.target))
        userDropdown.classList.add('hidden');
    });

    // Logout
    document.getElementById('logout-btn')?.addEventListener('click', (e) => {
      e.preventDefault();
      this.logout();
    });

    // Wire up login modal
    const loginOverlay = document.getElementById('login-modal-overlay');
    const loginBtn = document.getElementById('login-submit-btn');
    const loginUsernameEl = document.getElementById('login-username');
    const loginPasswordEl = document.getElementById('login-password');
    const loginError = document.getElementById('login-error');

    if (loginBtn) {
      loginBtn.addEventListener('click', async () => {
        const username = loginUsernameEl.value.trim();
        const password = loginPasswordEl.value;
        if (!username || !password) { loginError.style.display='block'; loginError.textContent='Enter username and password'; return; }
        loginBtn.textContent = 'Signing in...'; loginBtn.disabled = true;
        const ok = await this.login(username, password);
        loginBtn.textContent = 'Sign In'; loginBtn.disabled = false;
        if (ok) {
          loginOverlay.style.display = 'none';
          document.getElementById('user-name').textContent = this.user.username || 'User';
        } else {
          loginError.style.display = 'block'; loginError.textContent = 'Invalid credentials';
        }
      });
      // Enter key
      [loginUsernameEl, loginPasswordEl].forEach(el => el?.addEventListener('keydown', e => {
        if (e.key === 'Enter') loginBtn.click();
      }));
      // Close on overlay click
      loginOverlay?.addEventListener('click', e => { if (e.target === loginOverlay) loginOverlay.style.display='none'; });
    }
  },

  // ── Auth ────────────────────────────────────────────────────────────────────
  async login(username, password) {
    try {
      const r = await fetch(`${this.apiBase}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!r.ok) throw new Error('Invalid credentials');
      this.user = await r.json();
      // Persist token across page refreshes
      if (this.user.token) localStorage.setItem('auth_token', this.user.token);
      document.getElementById('user-name').textContent = this.user.username;
      this.showToast('Logged in', 'success');
      await this.loadSettings();
      this.updateAdminUI();
      return true;
    } catch (e) {
      this.showToast('Login failed: ' + e.message, 'error');
      return false;
    }
  },

  async logout() {
    const token = this.user?.token || localStorage.getItem('auth_token');
    // Notify backend to invalidate session
    try {
      await fetch(`${this.apiBase}/auth/logout`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
    } catch (e) { /* best effort */ }

    localStorage.removeItem('auth_token');
    this.user = null;
    this.settings = {};
    document.getElementById('user-name').textContent = 'Not logged in';
    document.getElementById('user-dropdown').classList.add('hidden');
    this.showToast('Logged out', 'info');
    this.updateAdminUI();
    this.navigate('dashboard');
  },

  updateAdminUI() {
    const isAdmin = this.isAdmin;
    document.querySelectorAll('.admin-only').forEach(el => {
      el.style.display = isAdmin ? '' : 'none';
    });
    // Re-run current page's render to update any inline admin-gated content
    if (this.currentPage === 'dashboard' && window.PageDashboard) {
      window.PageDashboard.render();
    }
    if (this.currentPage === 'crunchbase') {
      // If non-admin somehow on crunchbase page, redirect
      if (!isAdmin) {
        this.navigate('dashboard');
      } else {
        window.PageCrunchbase?.render();
      }
    }
  },

  async loadSettings() {
    if (!this.user) return;
    try {
      const r = await fetch(`${this.apiBase}/settings`);
      if (r.ok) this.settings = await r.json();
    } catch (e) { /* silent */ }
  },

  // ── Notifications ──────────────────────────────────────────────────────────
  addNotification(item) {
    this.notifications.unshift({ ...item, id: Date.now(), read: false });
    this.updateNotifBadge();
    this.renderNotifList();
  },

  updateNotifBadge() {
    const badge = document.getElementById('notif-badge');
    const unread = this.notifications.filter(n => !n.read).length;
    badge.textContent = unread;
    badge.classList.toggle('hidden', unread === 0);
  },

  renderNotifList() {
    const list = document.getElementById('notif-list');
    if (!this.notifications.length) {
      list.innerHTML = '<p class="empty-msg">No new notifications</p>';
      return;
    }
    list.innerHTML = this.notifications.slice(0, 10).map(n => `
      <a href="#" data-nav="${n.linkPage || 'leads'}" class="notif-item">
        <span>${n.read ? '🔘' : '🔵'}</span>
        <span style="flex:1">${n.message}</span>
        <span style="font-size:10px;color:var(--text-dim)">${n.time}</span>
      </a>
    `).join('');
  },

  // ── Toast ───────────────────────────────────────────────────────────────────
  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  },

  // ── Modals ──────────────────────────────────────────────────────────────────
  openModal(title, bodyHTML, footerHTML = '') {
    const overlay = document.getElementById('modal-overlay');
    const container = document.getElementById('modal-container');
    container.innerHTML = `
      <div class="modal-header">
        <div class="modal-title">${title}</div>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>
      <div class="modal-body">${bodyHTML}</div>
      ${footerHTML ? `<div class="modal-footer">${footerHTML}</div>` : ''}
    `;
    overlay.classList.remove('hidden');
    container.classList.remove('hidden');
  },

  closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
    document.getElementById('modal-container').classList.add('hidden');
  },

  // ── Helpers ────────────────────────────────────────────────────────────────
  formatDate(isoStr) {
    if (!isoStr) return '--';
    const d = new Date(isoStr);
    if (isNaN(d)) return isoStr;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  },

  relativeDate(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    if (isNaN(d)) return isoStr;
    const days = Math.round((Date.now() - d) / 86400000);
    if (days === 0) return 'today';
    if (days < 7) return `${days}d ago`;
    if (days < 30) return `${Math.floor(days/7)}w ago`;
    if (days < 365) return `${Math.floor(days/30)}mo ago`;
    return `${Math.floor(days/365)}y ago`;
  },

  numFmt(n) {
    if (n >= 1e9) return `$${(n/1e9).toFixed(1)}B`;
    if (n >= 1e6) return `$${(n/1e6).toFixed(1)}M`;
    if (n >= 1e3) return `$${(n/1e3).toFixed(0)}K`;
    return `$${n}`;
  },

  // ── Authenticated fetch wrapper ──────────────────────────────────────────────
  apiFetch(url, opts = {}) {
    const token = this.user?.token || localStorage.getItem('auth_token');
    return fetch(url, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        ...(opts.headers || {}),
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    }).then(r => {
      // Auto-detect session expiry and prompt login
      if (r.status === 401 && this.user) {
        const detail = r.headers.get('x-error-detail') || '';
        if (!this._showingLoginPrompt) {
          this._showingLoginPrompt = true;
          this.user = null;
          this.settings = {};
          localStorage.removeItem('auth_token');
          this.showToast('Session expired — please log in again', 'error');
          setTimeout(() => {
            document.getElementById('user-name').textContent = 'Not logged in';
            document.getElementById('login-modal-overlay').style.display = 'flex';
            this._showingLoginPrompt = false;
          }, 500);
        }
      }
      return r;
    });
  },
};

// ── Service Color Constants (shared across pages) ────────────────────────────
const SERVICE_COLORS = {
  'In Vivo / Mouse Services': '#FF6B6B',
  'DMPK': '#4ECDC4',
  'ADME': '#45B7D1',
  'Toxicology': '#F7DC6F',
  'Bioanalysis': '#BB8FCE',
  'CMC': '#52BE80',
  'Clinical Trials': '#F0B27A',
  'Regulatory Affairs': '#85C1E9',
  'Biomarker / Genomics': '#F1948A',
  'Protein Sciences / Biologics': '#A9DFBF',
};

const CRO_COLORS = [
  '#3b9eff','#2ecc71','#9b59b6','#e74c3c','#1abc9c',
  '#e67e22','#16a085','#8e44ad','#2980b9','#27ae60',
  '#d35400','#c0392b','#f5a623',
];

// ── Embedded Fallback (keeps the app working offline) ─────────────────────────
const FALLBACK_DATA = {
  "metadata":{"generated":"2026-04-30","source":"curated","version":"1.0"},
  "service_categories": [
    "In Vivo / Mouse Services","DMPK","ADME","Toxicology","Bioanalysis",
    "CMC","Clinical Trials","Regulatory Affairs","Biomarker / Genomics",
    "Protein Sciences / Biologics"
  ],
  "cros": [
    {"id":"charles_river","name":"Charles River Laboratories","short_name":"Charles River","website":"charlesriver.com","is_medicilon":false,"states":["MA","NJ","NC","PA","TX","CA","WA","MI","OH","NY"],"services":["In Vivo / Mouse Services","DMPK","ADME","Toxicology","Bioanalysis","CMC","Regulatory Affairs"],"tier":1},
    {"id":"covance","name":"Covance / Labcorp Drug Development","short_name":"Covance / Labcorp","website":"labcorp.com/drug-development","is_medicilon":false,"states":["WI","NJ","IN","TX","VA","NC","CA","CO"],"services":["DMPK","ADME","Toxicology","Bioanalysis","CMC","Clinical Trials","Regulatory Affairs","Biomarker / Genomics"],"tier":1},
    {"id":"wuxi","name":"WuXi AppTec","short_name":"WuXi AppTec","website":"wuxiapptec.com","is_medicilon":false,"states":["NJ","PA","GA","MN","CA","TX"],"services":["DMPK","ADME","Toxicology","Bioanalysis","CMC","Protein Sciences / Biologics"],"tier":1},
    {"id":"eurofins","name":"Eurofins Scientific","short_name":"Eurofins","website":"eurofins.com","is_medicilon":false,"states":["CA","PA","TX","NJ","NC","MO","WI","IL"],"services":["Bioanalysis","Toxicology","ADME","DMPK","CMC","Biomarker / Genomics"],"tier":1},
    {"id":"pharmaron","name":"Pharmaron","short_name":"Pharmaron","website":"pharmaron.com","is_medicilon":false,"states":["KY","CA","MD"],"services":["DMPK","ADME","Toxicology","Bioanalysis","CMC"],"tier":2},
    {"id":"crown_bio","name":"Crown Bioscience","short_name":"Crown Bioscience","website":"crownbio.com","is_medicilon":false,"states":["CA","NJ","TX"],"services":["In Vivo / Mouse Services","Biomarker / Genomics","Protein Sciences / Biologics"],"tier":2},
    {"id":"syneos","name":"Syneos Health","short_name":"Syneos Health","website":"syneoshealth.com","is_medicilon":false,"states":["NC","NJ","CA","TX","PA","FL","NY"],"services":["Clinical Trials","Regulatory Affairs","Biomarker / Genomics"],"tier":1},
    {"id":"icon","name":"ICON plc","short_name":"ICON plc","website":"iconplc.com","is_medicilon":false,"states":["CA","TX","NJ","NC","PA","MN","FL","NY"],"services":["Clinical Trials","Regulatory Affairs","Bioanalysis","DMPK"],"tier":1},
    {"id":"bioagilytix","name":"BioAgilytix","short_name":"BioAgilytix","website":"bioagilytix.com","is_medicilon":false,"states":["NC","MA","CA"],"services":["Bioanalysis","Biomarker / Genomics","Protein Sciences / Biologics"],"tier":2},
    {"id":"altasciences","name":"Altasciences","short_name":"Altasciences","website":"altasciences.com","is_medicilon":false,"states":["KS","WA","ND","QC"],"services":["Clinical Trials","DMPK","ADME","Toxicology","Bioanalysis"],"tier":2},
    {"id":"celerion","name":"Celerion","short_name":"Celerion","website":"celerion.com","is_medicilon":false,"states":["NE","AZ","NV","OR"],"services":["Clinical Trials","DMPK","ADME","Bioanalysis"],"tier":2},
    {"id":"biotrial","name":"Biotrial","short_name":"Biotrial","website":"biotrial.com","is_medicilon":false,"states":["NJ"],"services":["Clinical Trials","DMPK","Bioanalysis"],"tier":3},
    {"id":"medicilon","name":"Medicilon","short_name":"Medicilon","website":"medicilon.com","is_medicilon":true,"states":[],"services":["In Vivo / Mouse Services","DMPK","ADME","Toxicology","Bioanalysis","CMC","Protein Sciences / Biologics"],"tier":2,"core_services":["In Vivo / Mouse Services","DMPK","ADME","Toxicology","Bioanalysis","CMC"]},
  ],
  "biotech_hub_weights":{"MA":10,"CA":10,"NJ":9,"NC":8,"TX":8,"PA":7,"NY":7,"MD":6,"IL":6,"WA":6,"CO":5,"MN":5,"GA":4,"VA":4,"FL":4,"OH":3,"MI":3,"IN":3,"WI":3,"MO":3},
};

// ── Bootstrap ────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => App.init());
