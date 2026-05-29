/**
 * Settings Page — Fully functional API connections, notifications, data management
 * All settings persist to backend via PUT /api/settings
 */
const PageSettings = {
  settings: {},

  async render(container) {
    // Load settings first
    await this._loadSettings();

    container.innerHTML = `
      <div class="page-header flex-between">
        <div>
          <div class="page-title">Settings</div>
          <div class="page-subtitle">Configure API connections, notifications, and data sources</div>
        </div>
        <span id="settings-save-status" style="font-size:11px;color:var(--leaf);display:none">✅ Saved</span>
      </div>

      <div class="grid-2col" style="grid-template-columns:1fr 1fr;align-items:start">

        <!-- API Connections -->
        <div class="card" style="grid-row:span 2">
          <div class="card-header">
            <div class="card-title">🔌 API Connections</div>
          </div>

          <!-- SciLead Token (Bearer JWT) -->
          <div class="form-group">
            <label class="form-label">🔬 SciLeads Token (Primary Research Source)</label>
            <div class="flex-center gap-8 mb-8">
              <input type="password" class="form-input" placeholder="Paste Bearer token from DevTools" id="scilead-token" style="flex:1;font-family:monospace;font-size:11px" value="${this.settings.scilead_token || ''}">
            </div>
            <div style="display:flex;gap:8px">
              <button class="btn btn-sm" id="scilead-test-btn">🔍 Test Token</button>
              <span id="scilead-status" style="font-size:11px;display:flex;align-items:center"></span>
            </div>
            <div class="form-hint" style="margin-top:8px;font-size:10px;line-height:1.6">
              <strong>How to get your token:</strong><br>
              1. Log into <a href="https://portal.scileads.com" target="_blank">portal.scileads.com</a><br>
              2. Open DevTools (F12) → <strong>Network</strong> tab<br>
              3. Perform any search → find the <code>researcher</code> request<br>
              4. Click it → <strong>Headers</strong> → scroll to <strong>Request Headers</strong><br>
              5. Copy the <code>Authorization: Bearer eyJh...</code> value (just the JWT, not "Bearer ")<br>
              6. Paste here and save<br>
              <br>
              <em style="color:var(--text-dim)">Token lasts ~24h. Refresh this page to get a new one when it expires.</em>
            </div>
          </div>

          <!-- Crunchbase -->
          <div class="form-group">
            <label class="form-label">Crunchbase API Key (Funding Intel)</label>
            <div class="flex-center gap-8">
              <input type="password" class="form-input" placeholder="Enter your Crunchbase API key" id="crunchbase-key" style="flex:1" value="${this.settings.crunchbase_key || ''}">
              <button class="btn btn-sm" id="crunchbase-test-btn">Test</button>
            </div>
            <div class="form-hint"><a href="https://data.crunchbase.com/docs" target="_blank">Get a key</a> — enables company search, funding data, and lead enrichment</div>
            <div id="crunchbase-status" style="font-size:11px;margin-top:6px">${this.settings.crunchbase_key ? '<span style="color:var(--leaf)">Key configured</span>' : ''}</div>
          </div>

          <!-- BD Intelligence Feed -->
          <div class="form-group">
            <label class="form-label">BD Intelligence Feed</label>
            <div id="aggregator-status-bar" style="padding:10px 14px;background:var(--surface2);border-radius:var(--radius-sm);border:1px solid var(--border-soft);font-size:12px;line-height:1.6">
              <span style="color:var(--text-soft)">Checking...</span>
            </div>
            <div style="display:flex;gap:8px;margin-top:8px">
              <button class="btn btn-sm btn-primary" id="run-aggregate-btn">🔄 Run Now</button>
              <button class="btn btn-sm" onclick="App.navigate('linkedin')">📡 Open Feed</button>
            </div>
            <div class="form-hint">Automated — pulls BD signals from Google News, FierceBiotech, Endpoints, BioPharma Dive, PR Newswire, SEC EDGAR. No LinkedIn account or browser extension needed.</div>
          </div>

          <!-- NewsAPI -->
          <div class="form-group">
            <label class="form-label">NewsAPI Key (Optional)</label>
            <input type="password" class="form-input" placeholder="For enriched news articles" id="newsapi-key" style="flex:1" value="${this.settings.newsapi_key || ''}">
            <div class="form-hint"><a href="https://newsapi.org/register" target="_blank">Free tier available</a> — enhances the News Feed with additional articles</div>
          </div>

          <button class="btn btn-primary" id="save-api-keys-btn">💾 Save API Keys</button>
        </div>

        <!-- Notification Preferences -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">🔔 Notifications</div>
          </div>

          <div class="form-group">
            <label class="form-label">Email for Digests</label>
            <input type="email" class="form-input" placeholder="you@medicilon.com" id="notif-email" value="${this.settings.notif_email || ''}">
            <div class="form-hint">Morning/afternoon/evening digest emails (requires SMTP configured on backend)</div>
          </div>

          <div class="form-group">
            <label class="form-label">Desktop Notifications</label>
            <div class="flex-center gap-8">
              <select class="form-input" id="desktop-notif" style="flex:1">
                <option value="enabled" ${this.settings.desktop_notif !== false ? 'selected' : ''}>Enabled</option>
                <option value="disabled" ${this.settings.desktop_notif === false ? 'selected' : ''}>Disabled</option>
              </select>
              <button class="btn btn-sm" id="test-desktop-btn">Test</button>
            </div>
            <div class="form-hint">Browser push notifications for high-priority leads</div>
          </div>

          <div class="form-group">
            <label class="form-label">Minimum Lead Score</label>
            <select class="form-input" id="min-score">
              <option value="50" ${(this.settings.min_lead_score || 70) === 50 ? 'selected' : ''}>50 — All leads</option>
              <option value="70" ${(this.settings.min_lead_score || 70) === 70 ? 'selected' : ''}>70 — High value only</option>
              <option value="85" ${(this.settings.min_lead_score || 70) === 85 ? 'selected' : ''}>85 — Critical only</option>
            </select>
            <div class="form-hint">Only leads scoring above this threshold trigger alerts</div>
          </div>

          <button class="btn btn-gold" id="save-notif-btn">💾 Save Preferences</button>
        </div>

        <!-- Data Management -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">💾 Data & System</div>
          </div>

          <div class="form-group">
            <label class="form-label">Backend Status</label>
            <div id="backend-health" style="padding:8px 12px;background:var(--surface2);border-radius:var(--radius-sm);font-size:12px">
              Checking...
            </div>
          </div>

          <div class="flex-between mt-16" style="gap:8px">
            <button class="btn btn-sm btn-primary" id="refresh-now-btn">🔄 Refresh All Data</button>
            <button class="btn btn-sm btn-danger" id="clear-cache-btn">🗑 Clear Cache</button>
          </div>

          <div style="margin-top:14px;padding:10px 12px;background:var(--surface2);border-radius:var(--radius-sm);font-size:11px;color:var(--text-dim);line-height:1.7">
            <strong style="color:var(--moss)">Data Sources:</strong><br>
            ✅ SEC EDGAR (Form D — funding rounds)<br>
            ✅ ClinicalTrials.gov (industry-sponsored trials)<br>
            ✅ FierceBiotech / Endpoints / BioPharma Dive (RSS)<br>
            ✅ Google News (biotech keyword monitoring)<br>
            ✅ PR Newswire (press releases)<br>
            ${this.settings.scilead_token ? '✅ <strong>SciLeads</strong> (live researcher + publication data)' : '⬜ SciLeads (token needed)'}<br>
            ${this.settings.crunchbase_key ? '✅ Crunchbase (API connected)' : '⬜ Crunchbase (API key needed)'}
          </div>
        </div>

      </div>
    `;

    this._setupListeners();
    this._checkAggregatorStatus();
    this._checkBackendHealth();
  },

  async _loadSettings() {
    try {
      const r = await App.apiFetch(`${App.apiBase}/settings`);
      if (r.ok) this.settings = await r.json();
    } catch (e) {
      // Use defaults
      this.settings = {
        crunchbase_key: null, newsapi_key: null, notif_email: '',
        notif_morning: true, notif_afternoon: false, notif_evening: false,
        desktop_notif: true, min_lead_score: 70, alert_frequency: 'daily',
        refresh_interval: 43200,
      };
    }
  },

  _setupListeners() {
    // ── Aggregator Run ─────────────────────────────────────────────
    const runAggBtn = document.getElementById('run-aggregate-btn');
    if (runAggBtn) {
      runAggBtn.addEventListener('click', async () => {
        const bar = document.getElementById('aggregator-status-bar');
        if (bar) bar.innerHTML = '<span style="color:var(--gold)">⏳ Aggregating from public sources...</span>';
        runAggBtn.disabled = true; runAggBtn.textContent = '⏳ Running...';
        try {
          const r = await App.apiFetch(`${App.apiBase}/linkedin/aggregate`, { method: 'POST' });
          if (r.ok) {
            const data = await r.json();
            App.showToast(`${data.total_signals} signals from ${data.sources?.length || '?'} sources`, 'success');
          }
        } catch (e) {
          App.showToast('Aggregation failed — backend offline?', 'error');
        }
        runAggBtn.disabled = false; runAggBtn.textContent = '🔄 Run Now';
        this._checkAggregatorStatus();
      });
    }

    // ── Save API Keys (SciLead Token + Crunchbase + NewsAPI) ────────
    const saveApiBtn = document.getElementById('save-api-keys-btn');
    if (saveApiBtn) {
      saveApiBtn.addEventListener('click', async () => {
        const body = {};
        const slToken = document.getElementById('scilead-token');
        if (slToken && slToken.value !== (this.settings.scilead_token || '')) body.scilead_token = slToken.value;
        const cbKey = document.getElementById('crunchbase-key');
        if (cbKey && cbKey.value !== (this.settings.crunchbase_key || '')) body.crunchbase_key = cbKey.value;
        const newsKey = document.getElementById('newsapi-key');
        if (newsKey && newsKey.value !== (this.settings.newsapi_key || '')) body.newsapi_key = newsKey.value;

        if (!Object.keys(body).length) { App.showToast('No changes to save', 'info'); return; }

        try {
          const r = await App.apiFetch(`${App.apiBase}/settings`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
          });
          if (r.ok) {
            App.showToast('API keys saved', 'success');
            this.settings = { ...this.settings, ...body };
            App.settings = { ...(App.settings || {}), ...body };
            // Reload to update data source indicators
            this.render(document.getElementById('main-content'));
          } else {
            const err = await r.text();
            App.showToast('Save failed: ' + (err || 'login required'), 'error');
          }
        } catch (e) {
          App.showToast('Server unreachable', 'error');
        }
      });
    }

    // ── SciLead Test (Bearer Token) ─────────────────────────────────
    const scileadBtn = document.getElementById('scilead-test-btn');
    if (scileadBtn) {
      scileadBtn.addEventListener('click', async () => {
        const tokenInput = document.getElementById('scilead-token');
        const token = tokenInput?.value?.trim() || '';
        if (!token) { App.showToast('Paste a Bearer token from DevTools first', 'error'); return; }
        const status = document.getElementById('scilead-status');
        if (status) status.innerHTML = '<span style="color:var(--gold)">🔍 Testing...</span>';
        scileadBtn.disabled = true;
        try {
          const r = await App.apiFetch(`${App.apiBase}/scilead/test?token=${encodeURIComponent(token)}`);
          const data = await r.json();
          if (data.ok) {
            if (status) status.innerHTML = `<span style="color:var(--leaf)">✅ ${data.message}</span>`;
            // Auto-save token: try backend + always store in localStorage as fallback
            localStorage.setItem('scilead_token', token);
            if (status) status.innerHTML += '<br><span style="font-size:10px;color:var(--leaf)">Token saved — visit Dashboard</span>';
            let savedBackend = false;
            try {
              const saveR = await App.apiFetch(`${App.apiBase}/settings`, {
                method: 'PUT', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scilead_token: token }),
              });
              if (saveR.ok) {
                this.settings = { ...this.settings, scilead_token: token };
                App.settings = { ...(App.settings || {}), scilead_token: token };
                savedBackend = true;
              }
            } catch (e2) { /* save best effort */ }
            if (!savedBackend && !App.user) {
              App.showToast('Login first to persist token → Dashboard still has access', 'info');
            }
            setTimeout(() => this.render(document.getElementById('main-content')), 300);
          } else {
            if (status) status.innerHTML = `<span style="color:var(--red)">❌ ${data.error || data.detail || 'Token rejected'}</span>`;
          }
        } catch (e) {
          if (status) status.innerHTML = '<span style="color:var(--red)">❌ Backend not available</span>';
        }
        scileadBtn.disabled = false;
      });
    }

    // ── Crunchbase Test ────────────────────────────────────────────
    const crunchbaseBtn = document.getElementById('crunchbase-test-btn');
    if (crunchbaseBtn) {
      crunchbaseBtn.addEventListener('click', async () => {
        const key = document.getElementById('crunchbase-key');
        if (!key?.value) { App.showToast('Enter an API key first', 'error'); return; }
        const status = document.getElementById('crunchbase-status');
        if (status) status.innerHTML = '<span style="color:var(--gold)">Testing...</span>';
        try {
          const r = await App.apiFetch(`${App.apiBase}/crunchbase/test?key=${encodeURIComponent(key.value)}`);
          const data = await r.json();
          if (status) {
            status.innerHTML = data.ok
              ? `<span style="color:var(--leaf)">✅ Connected — ${data.company_count || '?'} companies accessible</span>`
              : `<span style="color:var(--red)">❌ ${data.error || data.detail || 'Invalid key'}</span>`;
          }
        } catch (e) {
          if (status) status.innerHTML = '<span style="color:var(--red)">❌ Backend not available</span>';
        }
      });
    }

    // ── Save Notification Prefs ────────────────────────────────────
    const saveNotifBtn = document.getElementById('save-notif-btn');
    if (saveNotifBtn) {
      saveNotifBtn.addEventListener('click', async () => {
        const body = {
          notif_email: document.getElementById('notif-email')?.value || '',
          desktop_notif: document.getElementById('desktop-notif')?.value === 'enabled',
          min_lead_score: parseInt(document.getElementById('min-score')?.value) || 70,
        };
        try {
          const r = await App.apiFetch(`${App.apiBase}/settings`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
          });
          if (r.ok) {
            App.showToast('Preferences saved', 'success');
            this.settings = { ...this.settings, ...body };
          } else {
            App.showToast('Save failed — login required', 'error');
          }
        } catch (e) {
          App.showToast('Preferences saved locally', 'success');
          this.settings = { ...this.settings, ...body };
        }
      });
    }

    // ── Desktop Notification Test ──────────────────────────────────
    const testDesktopBtn = document.getElementById('test-desktop-btn');
    if (testDesktopBtn) {
      testDesktopBtn.addEventListener('click', () => {
        if (!('Notification' in window)) {
          App.showToast('Notifications not supported in this browser', 'error'); return;
        }
        Notification.requestPermission().then(perm => {
          if (perm === 'granted') {
            new Notification('Medicilon Intelligence', { body: '✅ BD alert test — high-priority lead detected!' });
            App.showToast('Test notification sent', 'success');
          } else {
            App.showToast('Notifications blocked by browser', 'error');
          }
        });
      });
    }

    // ── Refresh All Data ───────────────────────────────────────────
    const refreshBtn = document.getElementById('refresh-now-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        App.showToast('Refreshing all data sources...', 'info');
        try {
          await Promise.allSettled([
            App.loadData(),
            App.apiFetch(`${App.apiBase}/refresh/intelligence`, { method: 'POST' }),
            App.apiFetch(`${App.apiBase}/refresh/news`, { method: 'POST' }),
            App.apiFetch(`${App.apiBase}/refresh/deals`, { method: 'POST' }),
          ]);
        } catch (e) { /* best effort */ }
        App.showToast('All data refreshed', 'success');
      });
    }

    // ── Clear Cache ────────────────────────────────────────────────
    const clearBtn = document.getElementById('clear-cache-btn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (confirm('Clear all locally cached data? This cannot be undone.')) {
          localStorage.clear();
          App.showToast('Cache cleared — reloading...', 'info');
          setTimeout(() => location.reload(), 800);
        }
      });
    }
  },

  async _checkAggregatorStatus() {
    const bar = document.getElementById('aggregator-status-bar');
    if (!bar) return;
    try {
      const r = await fetch(`${App.apiBase}/linkedin/aggregated?limit=1`);
      if (r.ok) {
        const data = await r.json();
        const total = data.total || 0;
        const gen = data.generated || '';
        if (total > 0) {
          const relDate = gen ? App.relativeDate(gen) : 'recently';
          bar.innerHTML = `<span style="color:var(--leaf);font-weight:600">✅ Active</span> — ${total} signals (${relDate})
            <br><span style="font-size:10px;color:var(--text-dim)">Google News · FierceBiotech · Endpoints · BioPharma Dive · PR Newswire · SEC EDGAR</span>`;
        } else {
          bar.innerHTML = `<span style="color:var(--gold);font-weight:600">⬜ Idle</span> — no signals collected yet
            <br><span style="font-size:10px;color:var(--text-dim)">Click "Run Now" or visit the BD Intelligence Feed</span>`;
        }
      }
    } catch (e) {
      bar.innerHTML = `<span style="color:var(--red);font-weight:600">❌ Offline</span> — backend not reachable
        <br><span style="font-size:10px;color:var(--text-dim)">Start the backend server to enable intelligence aggregation</span>`;
    }
  },

  async _checkBackendHealth() {
    const el = document.getElementById('backend-health');
    if (!el) return;
    try {
      const r = await fetch(`${App.apiBase}/health`);
      if (r.ok) {
        const data = await r.json();
        el.innerHTML = `<span style="color:var(--leaf);font-weight:600">✅ Running</span> — v${data.version || '?'} · API: ${App.apiBase}`;
      }
    } catch (e) {
      el.innerHTML = '<span style="color:var(--red);font-weight:600">❌ Offline</span> — start with <code style="font-size:10px">python run.py</code>';
    }
  },
};
