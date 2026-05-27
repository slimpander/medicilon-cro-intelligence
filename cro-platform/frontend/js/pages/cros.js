/**
 * CRO Profiles Page — Competitive intelligence on each CRO
 */
const PageCros = {
  render(container) {
    const data = App.croData;
    if (!data || !data.cros || !data.cros.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-title">No CRO data available</div><div class="empty-state-desc">Check that cro_data.json is loaded</div></div>';
      return;
    }

    const med = data.cros.find(c => c && c.is_medicilon) || null;
    const competitors = (data.cros || []).filter(c => c && !c.is_medicilon)
      .sort((a, b) => (a.tier || 5) - (b.tier || 5));

    container.innerHTML = `
      <div class="page-header">
        <div class="page-title">CRO Competitive Profiles</div>
        <div class="page-subtitle">${competitors.length} competitors tracked · ${data.service_categories?.length || 10} service categories</div>
      </div>

      <!-- Medicilon Card (highlighted) -->
      ${med ? `
      <div class="card mb-24" style="border:1px solid var(--gold-border);background:linear-gradient(135deg,var(--surface),var(--gold-dim))">
        <div class="flex-between mb-12">
          <div>
            <div class="card-title" style="color:var(--gold)">⭐ ${med.name}</div>
            <div style="font-size:11px;color:var(--text-muted)">Our Position</div>
          </div>
          <span class="tag tag-gold">Tier ${med.tier || 2}</span>
        </div>
        <p style="font-size:12px;color:var(--text-muted);line-height:1.6;margin-bottom:12px">${med.summary || med.description || ''}</p>
        <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px">
          ${(med.core_services || med.services || []).map(s => {
            const c = SERVICE_COLORS[s] || '#888';
            return `<span class="tag" style="background:${c}22;border-color:${c}44;color:${c}">${s}</span>`;
          }).join('')}
        </div>
        <div class="flex-between" style="font-size:11px">
          <span class="text-dim">US Presence: ${med.states?.length ? `${med.states.length} states` : 'No US offices — gap analysis recommended'}</span>
          ${med.website_url ? `<a href="${med.website_url}" target="_blank">🌐 Website →</a>` : ''}
        </div>
      </div>
      ` : ''}

      <!-- Competitor Grid -->
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px">
        ${competitors.map((cro, i) => {
          const col = CRO_COLORS[i % CRO_COLORS.length];
          const svcHtml = (cro.services || []).slice(0, 8).map(s => {
            const c = SERVICE_COLORS[s] || '#888';
            return `<span class="tag" style="background:${c}22;border-color:${c}44;color:${c}">${s.split(' / ')[0]}</span>`;
          }).join('');

          // Compare with Medicilon
          const medSvcs = new Set(med?.core_services || med?.services || []);
          const overlap = (cro.services || []).filter(s => medSvcs.has(s)).length;
          const totalMed = medSvcs.size;
          const overlapPct = totalMed ? Math.round(overlap / totalMed * 100) : 0;

          return `
          <div class="card" style="cursor:pointer" onclick="PageCros.openDetail('${cro.id}')">
            <div class="flex-between mb-8">
              <div class="flex-center gap-8">
                <span style="width:10px;height:10px;border-radius:50%;background:${col};flex-shrink:0"></span>
                <strong style="font-size:13px">${cro.short_name}</strong>
              </div>
              <span class="tag tag-default">Tier ${cro.tier || '-'}</span>
            </div>
            <div class="flex-between mb-8" style="font-size:10px;color:var(--text-dim)">
              <span>${cro.states?.length || 0} US states</span>
              <span>${cro.services?.length || 0} services</span>
            </div>
            <div style="font-size:11px;color:var(--text-muted);line-height:1.4;margin-bottom:8px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">
              ${cro.description || ''}
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:3px;margin-bottom:8px">${svcHtml}</div>
            <div style="display:flex;align-items:center;gap:6px">
              <div style="flex:1;height:4px;background:var(--surface3);border-radius:2px;overflow:hidden">
                <div style="height:100%;border-radius:2px;background:${overlapPct >= 70 ? 'var(--red)' : overlapPct >= 40 ? 'var(--orange)' : 'var(--accent)'};width:${overlapPct}%"></div>
              </div>
              <span style="font-size:10px;color:var(--text-dim);white-space:nowrap">${overlapPct}% overlap</span>
            </div>
          </div>`;
        }).join('')}
      </div>

      <!-- Service Overlap Matrix -->
      <div class="card mt-24">
        <div class="card-header">
          <div class="card-title">📊 Service Overlap Heatmap (vs Medicilon)</div>
        </div>
        <div style="overflow-x:auto" id="overlap-matrix"></div>
      </div>
    `;

    this.renderMatrix();
  },

  openDetail(croId) {
    const cro = App.croData.cros.find(c => c.id === croId);
    if (!cro) return;

    const med = App.croData.cros.find(c => c.is_medicilon);
    const medSvcs = new Set(med?.core_services || med?.services || []);
    const overlap = (cro.services || []).filter(s => medSvcs.has(s));
    const missing = [...medSvcs].filter(s => !(cro.services || []).includes(s));

    App.openModal(cro.name, `
      <div class="flex-between mb-12">
        <span class="tag tag-gold">Tier ${cro.tier || '-'}</span>
        <span class="text-dim">${cro.states?.length || 0} US states · ${cro.services?.length || 0} services</span>
      </div>

      <p style="font-size:13px;color:var(--text-muted);line-height:1.6;margin-bottom:16px">${cro.summary || cro.description || 'No description available.'}</p>

      <div class="grid-2col mb-12" style="grid-template-columns:1fr 1fr">
        <div>
          <div class="card-title mb-8">✅ Services Overlapping with Medicilon</div>
          <div style="display:flex;flex-wrap:wrap;gap:4px">
            ${overlap.map(s => {
              const c = SERVICE_COLORS[s] || '#888';
              return `<span class="tag tag-green">${s}</span>`;
            }).join('') || '<span class="text-dim">None</span>'}
          </div>
        </div>
        <div>
          <div class="card-title mb-8">🚫 Medicilon Services NOT Covering</div>
          <div style="display:flex;flex-wrap:wrap;gap:4px">
            ${missing.map(s => `<span class="tag tag-red">${s}</span>`).join('') || '<span class="text-dim">Full overlap</span>'}
          </div>
        </div>
      </div>

      <div class="card-title mb-8">All Services</div>
      <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px">
        ${(cro.services || []).map(s => {
          const c = SERVICE_COLORS[s] || '#888';
          const isOverlap = medSvcs.has(s);
          return `<span class="tag" style="background:${c}22;border-color:${c}44;color:${c}">${s}${isOverlap ? ' ⚡' : ''}</span>`;
        }).join('')}
      </div>

      ${cro.states?.length ? `
        <div class="card-title mb-8">US Locations</div>
        <div style="display:flex;flex-wrap:wrap;gap:4px">${cro.states.map(s => `<span class="tag tag-default">${s}</span>`).join('')}</div>
      ` : ''}

      <div class="mt-16">
        ${cro.website_url ? `<a href="${cro.website_url}" target="_blank" class="btn btn-primary btn-sm">🌐 Visit Website</a>` : ''}
      </div>
    `);
  },

  renderMatrix() {
    const el = document.getElementById('overlap-matrix');
    if (!el) return;

    const data = App.croData;
    const med = data.cros.find(c => c.is_medicilon);
    const medSvcs = med?.core_services || med?.services || [];
    const medSet = new Set(medSvcs);  // for .has() lookups
    const competitors = (data.cros || []).filter(c => !c.is_medicilon);

    if (!medSvcs.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-state-desc">No Medicilon services defined</div></div>';
      return;
    }

    el.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>CRO</th>
            ${medSvcs.map(s => `<th style="text-align:center;font-size:9px;max-width:80px">${s.split(' / ')[0]}</th>`).join('')}
            <th style="text-align:center">Coverage</th>
          </tr>
        </thead>
        <tbody>
          ${competitors.map(cro => `
            <tr>
              <td><strong style="font-size:12px">${cro.short_name}</strong></td>
              ${medSvcs.map(s => {
                const has = (cro.services || []).includes(s);
                return `<td style="text-align:center">${has ? '✅' : '—'}</td>`;
              }).join('')}
              <td style="text-align:center">
                <span style="color:${(cro.services||[]).filter(s=>medSet.has(s)).length >= 5 ? 'var(--red)' : 'var(--text-dim)'}">
                  ${(cro.services||[]).filter(s=>medSet.has(s)).length}/${medSvcs.length}
                </span>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>

      <div style="padding:12px;background:var(--surface2);border-radius:var(--radius-sm);margin-top:12px;font-size:12px;color:var(--gold);text-align:center">
        💡 <strong>Medicilon differentiator:</strong> ${medSvcs.filter(s => competitors.every(c => !(c.services||[]).includes(s))).join(', ') || 'Be the cost-competitive alternative — Chinese CRO pricing with IND-ready compliance'}
      </div>
    `;
  },
};
