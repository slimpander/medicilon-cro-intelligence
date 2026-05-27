/**
 * Lead Intelligence Page — Funding leads from SEC/Crunchbase/NIH + service matching
 */
const TIER_COLORS = { S: '#27AE60', A: '#2E75B6', B: '#F5A623', C: '#E67E22', D: '#999' };

const PageLeads = {
  filters: { source: '', stage: '', state: '', need: '' },
  aiScores: null,

  render(container) {
    const data = App.croData;
    const intel = App.intelligenceData;
    const leads = intel?.leads || [];

    container.innerHTML = `
      <div class="page-header flex-between">
        <div>
          <div class="page-title">Lead Intelligence</div>
          <div class="page-subtitle">
            <span id="leads-meta">
              ${intel ? `${leads.length} active leads · Sources: ClinicalTrials.gov + SEC EDGAR` : 'Static curated data'}
            </span>
          </div>
        </div>
        <div class="flex-center gap-8">
          <button class="btn btn-sm btn-gold" id="leads-ai-score-btn">🤖 AI Score</button>
          <button class="btn btn-sm" id="leads-refresh-btn">🔄 Refresh</button>
          <button class="btn btn-sm btn-primary" id="leads-export-btn">📋 Export</button>
        </div>
      </div>

      <!-- Filter Bar -->
      <div class="filter-bar" id="leads-filters">
        <select id="filter-source">
          <option value="">All Sources</option>
          <option>ClinicalTrials.gov</option>
          <option>SEC EDGAR</option>
          <option>NIH RePORTER</option>
        </select>
        <select id="filter-stage">
          <option value="">All Stages</option>
          <option>Phase 1</option>
          <option>Phase 2</option>
          <option>Phase 3</option>
          <option>Funding</option>
          <option>Grant</option>
          <option>Preclinical</option>
        </select>
        <select id="filter-state">
          <option value="">All States</option>
          ${['MA','CA','NJ','NC','TX','PA','NY','MD','IL','WA','CO','FL','GA','VA'].map(s => `<option>${s}</option>`).join('')}
        </select>
        <select id="filter-need">
          <option value="">All Service Needs</option>
          ${(data?.service_categories || []).map(s => `<option>${s}</option>`).join('')}
        </select>
        <span class="filter-spacer"></span>
        <span style="font-size:11px;color:var(--text-dim)" id="leads-count"></span>
      </div>

      <!-- Leads Grid -->
      <div id="leads-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px">
        <div class="empty-state">
          <div class="empty-state-icon">🔍</div>
          <div class="empty-state-title">Loading leads...</div>
        </div>
      </div>
    `;

    this.wireFilters();
    this.renderCards();
  },

  wireFilters() {
    const map = { 'filter-source': 'source', 'filter-stage': 'stage', 'filter-state': 'state', 'filter-need': 'need' };
    Object.entries(map).forEach(([elId, key]) => {
      document.getElementById(elId)?.addEventListener('change', (e) => {
        this.filters[key] = e.target.value.startsWith('All') ? '' : e.target.value;
        this.renderCards();
      });
    });

    document.getElementById('leads-ai-score-btn')?.addEventListener('click', async () => {
      await this.aiScore();
    });

    document.getElementById('leads-refresh-btn')?.addEventListener('click', async () => {
      App.showToast('Refreshing lead data...', 'info');
      await App.loadData();
      this.renderCards();
      App.showToast('Leads refreshed', 'success');
    });

    document.getElementById('leads-export-btn')?.addEventListener('click', () => {
      this.exportLeads();
    });
  },

  // ── AI Scoring ────────────────────────────────────────────────────────
  async aiScore() {
    const btn = document.getElementById('leads-ai-score-btn');
    const leads = App.intelligenceData?.leads || [];
    if (!leads.length) {
      App.showToast('No leads to score', 'error');
      return;
    }

    btn.disabled = true;
    btn.textContent = '⏳ Scoring...';
    App.showToast(`Scoring ${leads.length} leads with AI...`, 'info');

    try {
      const r = await App.apiFetch(`${App.apiBase}/leads/score-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ leads }),
      });

      if (!r.ok) throw new Error('Scoring API unavailable');

      const data = await r.json();
      this.aiScores = {};
      (data.leads || []).forEach(l => {
        this.aiScores[l.source_id || l.name] = l;
      });

      App.showToast(
        `AI scored: ${data.summary.tier_s} tier-S, ${data.summary.tier_a} tier-A, ${data.summary.tier_b} tier-B`,
        'success'
      );
      this.renderCards();
    } catch (e) {
      console.warn('[Leads] AI scoring unavailable, using local fallback');
      App.showToast('AI scoring unavailable — using built-in relevance scores', 'warning');
    }

    btn.disabled = false;
    btn.textContent = '🤖 AI Score';
  },

  renderCards() {
    const grid = document.getElementById('leads-grid');
    const countEl = document.getElementById('leads-count');
    if (!grid) return;

    const intel = App.intelligenceData;
    const data = App.croData;
    const focal = data?.cros?.find(c => c.is_medicilon);
    const focalSvcs = new Set(focal ? (focal.core_services || focal.services || []) : []);

    let leads = intel?.leads || [];
    if (!leads.length) {
      grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
        <div class="empty-state-icon">📭</div>
        <div class="empty-state-title">No leads found</div>
        <div class="empty-state-desc">Run fetch_intelligence.py to pull live funding data</div>
      </div>`;
      return;
    }

    // Apply filters
    let filtered = leads.filter(l => {
      if (this.filters.source && l.source !== this.filters.source) return false;
      if (this.filters.stage && l.stage !== this.filters.stage) return false;
      if (this.filters.state && l.state !== this.filters.state) return false;
      if (this.filters.need && !(l.needs || []).includes(this.filters.need)) return false;
      return true;
    });

    // Use AI scores if available, otherwise fall back to heuristic
    if (this.aiScores) {
      filtered.forEach(l => {
        const key = l.source_id || l.name;
        const ai = this.aiScores[key];
        if (ai) {
          l._aiScore = ai.total_score;
          l._aiTier = ai.tier;
          l._aiExplanation = ai.explanation;
          l._aiBreakdown = ai.breakdown;
          l._aiPriority = ai.bd_priority;
          l._display = ai.total_score;
        } else {
          // Fallback for unscored
          const overlap = (l.needs || []).filter(n => focalSvcs.has(n)).length;
          const hubW = (data?.biotech_hub_weights || {})[l.state] || l.hub_weight || 0;
          l._display = overlap * 15 + hubW * 4 + (l.score || 0) * 0.3;
        }
      });
    } else {
      // Heuristic fallback
      filtered.forEach(l => {
        const overlap = (l.needs || []).filter(n => focalSvcs.has(n)).length;
        const hubW = (data?.biotech_hub_weights || {})[l.state] || l.hub_weight || 0;
        l._display = overlap * 15 + hubW * 4 + (l.score || 0) * 0.3;
      });
    }
    filtered.sort((a, b) => b._display - a._display);

    if (countEl) countEl.textContent = `${filtered.length} leads`;

    const SOURCE_COLORS = {
      'ClinicalTrials.gov': '#3b9eff',
      'SEC EDGAR': '#2ecc71',
      'NIH RePORTER': '#9b59b6',
      'Crunchbase': '#f5a623',
    };
    const STAGE_COLORS = {
      'Phase 1': '#3b9eff', 'Phase 2': '#2ecc71', 'Phase 3': '#1abc9c',
      'Funding': '#e67e22', 'Seed/Funding': '#e67e22', 'Public': '#f5a623',
      'Grant': '#9b59b6', 'Preclinical': '#e74c3c',
    };

    grid.innerHTML = filtered.map(l => {
      const overlap = (l.needs || []).filter(n => focalSvcs.has(n));
      const missing = (l.needs || []).filter(n => !focalSvcs.has(n));
      const matchPct = l.needs?.length ? Math.round(overlap.length / l.needs.length * 100) : 0;
      const stageColor = STAGE_COLORS[l.stage] || '#888';
      const sourceColor = SOURCE_COLORS[l.source] || '#888';
      const score = Math.round(l._display || l.score || 0);
      const aiTierBadge = l._aiTier
        ? `<span class="tag" style="background:${TIER_COLORS[l._aiTier] || '#888'};color:white;font-size:9px;margin-left:4px">${l._aiTier}</span>`
        : '';

      // Funding amount display
      const amountStr = l.recent_round_amount_display || l.total_funding_display || '';
      const hasCrunchbase = l.source === 'Crunchbase' || l.total_funding_usd;

      return `
        <div class="card" style="cursor:pointer;padding:14px" onclick="PageLeads.openDetail('${(l.source_id || l.name).replace(/'/g, "\\'")}')">
          <div class="flex-between mb-8">
            <div class="flex-center gap-8">
              <span style="width:8px;height:8px;border-radius:50%;background:${stageColor};flex-shrink:0"></span>
              <strong style="font-size:13px">${l.name}</strong>
              ${hasCrunchbase ? '<span class="tag tag-gold" style="font-size:9px">💰</span>' : ''}
            </div>
            <span class="score-pill ${score >= 80 ? 'score-high' : score >= 60 ? 'score-med' : 'score-low'}">${score}${aiTierBadge}</span>
          </div>
          <div class="flex-between mb-8" style="font-size:10px;color:var(--text-dim)">
            <span>${l.state || 'US'} · ${l.stage} · ${App.relativeDate(l.date)}</span>
            <span class="tag" style="font-size:9px;background:${sourceColor}22;border-color:${sourceColor}44;color:${sourceColor}">${l.source}</span>
          </div>
          ${amountStr ? `<div style="font-size:12px;font-weight:600;color:var(--gold);margin-bottom:4px">${amountStr}</div>` : ''}
          <div style="font-size:11px;color:var(--text-muted);line-height:1.4;margin-bottom:6px">
            ${(l.focus || l.signal || '').slice(0, 100)}
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:3px">
            ${overlap.map(n => {
              const c = SERVICE_COLORS[n] || '#888';
              return `<span class="tag tag-green">✓ ${n}</span>`;
            }).join('')}
            ${missing.map(n => `<span class="tag tag-default">${n}</span>`).join('')}
          </div>
          ${matchPct >= 80 ? '<div class="mt-8" style="font-size:10px;color:var(--gold)">⭐ Strong match — ' + matchPct + '% service overlap</div>' : ''}
          ${l.lead_investors?.length ? `<div style="font-size:9px;color:var(--text-dim);margin-top:4px">Investors: ${l.lead_investors.slice(0,3).join(', ')}</div>` : ''}
        </div>
      `;
    }).join('') || `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-state-desc">No leads match current filters</div>
    </div>`;
  },

  openDetail(sourceId) {
    const leads = App.intelligenceData?.leads || [];
    const l = leads.find(l => l.source_id === sourceId || l.name === sourceId);
    if (!l) return;

    const score = l.score || 0;
    const focalSvcs = new Set((App.croData?.cros?.find(c => c.is_medicilon)?.core_services || []));
    const overlap = (l.needs || []).filter(n => focalSvcs.has(n));
    const missing = (l.needs || []).filter(n => !focalSvcs.has(n));

    // Enriched fields
    const hasFundingData = l.total_funding_usd || l.recent_round_amount_usd;
    const fundingRows = hasFundingData ? `
        <div>
          <div class="form-label">Total Funding</div>
          <span style="font-size:18px;font-weight:700;color:var(--gold)">${l.total_funding_display || ''}</span>
        </div>
        <div>
          <div class="form-label">Recent Round</div>
          <span style="font-size:14px;color:var(--text)">${l.recent_round_amount_display || ''}</span>
        </div>` : '';

    const linkedinLink = l.linkedin_url ? `<a href="${l.linkedin_url}" target="_blank" class="btn btn-sm">🔗 LinkedIn →</a>` : '';
    const websiteLink = l.website ? `<a href="${l.website}" target="_blank" class="btn btn-sm btn-primary">🌐 Website →</a>` : '';
    const cbLink = l.url && l.source === 'Crunchbase' ? `<a href="${l.url}" target="_blank" class="btn btn-sm btn-gold">📊 Crunchbase →</a>` : '';

    const investorSection = l.lead_investors?.length ? `
      <div class="card-title mb-8 mt-12">Lead Investors</div>
      <div style="display:flex;flex-wrap:wrap;gap:4px">${l.lead_investors.map(i => `<span class="tag tag-gold">${i}</span>`).join('')}</div>
    ` : '';

    App.openModal(l.name, `
      <div class="flex-between mb-12">
        <span class="score-pill ${score >= 80 ? 'score-high' : score >= 60 ? 'score-med' : 'score-low'}">Score: ${score}</span>
        <span class="tag tag-gold">${l.state || 'US'} · Biotech Hub</span>
      </div>

      <div class="grid-2col mb-12" style="grid-template-columns:1fr 1fr">
        <div>
          <div class="form-label">Source</div>
          <span class="tag tag-default">${l.source}</span>
        </div>
        <div>
          <div class="form-label">Stage</div>
          <span class="tag tag-accent">${l.stage}</span>
        </div>
        <div>
          <div class="form-label">Date</div>
          <span style="font-size:13px">${App.formatDate(l.date)} (${App.relativeDate(l.date)})</span>
        </div>
        <div>
          <div class="form-label">City</div>
          <span style="font-size:12px;color:var(--text-muted)">${l.city || 'N/A'}</span>
        </div>
        ${fundingRows}
      </div>

      ${l.focus ? `<div class="card-title mb-8">Focus</div><p style="font-size:13px;color:var(--text-muted);line-height:1.6;margin-bottom:12px">${l.focus}</p>` : ''}
      <div class="card-title mb-8">Signal</div>
      <p style="font-size:13px;color:var(--text-muted);line-height:1.6;margin-bottom:12px">${l.signal || 'No additional signal data'}</p>

      ${investorSection}

      <div class="card-title mb-8 mt-12">Medicilon Service Match</div>
      <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px">
        ${overlap.map(n => {
          const c = SERVICE_COLORS[n] || '#888';
          return `<span class="tag tag-green">✓ ${n}</span>`;
        }).join('')}
        ${missing.map(n => `<span class="tag tag-default">${n}</span>`).join('')}
        ${!l.needs?.length ? '<span class="text-dim">No service needs identified</span>' : ''}
      </div>

      <div style="display:flex;gap:6px;margin-top:16px;flex-wrap:wrap">
        ${websiteLink}
        ${linkedinLink}
        ${cbLink}
        ${l.url && l.source !== 'Crunchbase' ? `<a href="${l.url}" target="_blank" class="btn btn-sm btn-primary">🔗 View Source →</a>` : ''}
      </div>

      <div class="mt-16 card-title mb-8">💡 BD Action Items</div>
      <ul style="font-size:12px;color:var(--text-muted);padding-left:16px;line-height:1.8">
        ${overlap.length ? `<li>Medicilon covers ${overlap.length}/${l.needs?.length || 0} of their service needs — reach out with a capability deck</li>` : ''}
        ${l.stage === 'Funding' || l.stage === 'Seed/Funding' ? '<li>Recent funding suggests upcoming CRO spend — timing is now</li>' : ''}
        ${l.stage?.includes('Phase') ? '<li>Clinical trial starting — likely need DMPK/Tox/Bioanalysis support</li>' : ''}
        ${hasFundingData ? `<li>${l.total_funding_display ? 'Total funding of ' + l.total_funding_display + ' — significant CRO budget opportunity' : ''}</li>` : ''}
        <li>Find decision-makers on LinkedIn (CSO, VP R&D, Head of Preclinical)</li>
      </ul>
    `);
  },

  exportLeads() {
    const leads = App.intelligenceData?.leads || [];
    const csv = ['Name,State,Stage,Source,Date,Needs,Score']
      .concat(leads.map(l => `"${l.name}","${l.state}","${l.stage}","${l.source}","${l.date}","${(l.needs||[]).join(';')}","${l.score}"`))
      .join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `medicilon-leads-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    App.showToast('Leads exported as CSV', 'success');
  },
};
