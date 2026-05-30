/**
 * Analytics & Visualizations Page — Premium styling
 * Fancy Chart.js charts with gradients, animations, shadows, and rich tooltips.
 */
const PageAnalytics = {
  charts: [],
  data: null,

  // ── Color Palettes ─────────────────────────────────────────────────────────
  PALETTES: {
    primary:   ['#818cf8','#6366f1','#4f46e5','#4338ca','#3730a3','#312e81'],
    ocean:     ['#67e8f9','#22d3ee','#06b6d4','#0891b2','#0e7490','#155e75'],
    forest:    ['#6ee7b7','#34d399','#10b981','#059669','#047857','#065f46'],
    sunset:    ['#fcd34d','#fbbf24','#f59e0b','#d97706','#b45309','#92400e'],
    rose:      ['#fda4af','#fb7185','#f43f5e','#e11d48','#be123c','#9f1239'],
    lavender:  ['#c4b5fd','#a78bfa','#8b5cf6','#7c3aed','#6d28d9','#5b21b6'],
  },

  // ── Gradient Helpers ───────────────────────────────────────────────────────
  _createGradient(ctx, colors, vertical = false) {
    const gradient = vertical
      ? ctx.createLinearGradient(0, 0, 0, ctx.canvas.height)
      : ctx.createLinearGradient(0, 0, ctx.canvas.width, 0);
    colors.forEach((c, i) => gradient.addColorStop(i / (colors.length - 1), c));
    return gradient;
  },

  _createBarGradient(ctx, topColor, bottomColor) {
    const g = ctx.createLinearGradient(0, 0, 0, ctx.canvas.clientHeight || 200);
    g.addColorStop(0, topColor);
    g.addColorStop(1, bottomColor);
    return g;
  },

  async render(container) {
    container.innerHTML = `
      <div class="page-header flex-between" style="animation:fadeIn 0.5s ease">
        <div>
          <div class="page-title">📈 Analytics & Insights</div>
          <div class="page-subtitle">Real-time CRO intelligence visualization</div>
        </div>
        <div class="flex-center gap-8">
          <span style="font-size:11px;color:var(--text-dim)" id="analytics-updated"></span>
          <button class="btn btn-primary btn-sm" id="analytics-refresh-btn">🔄 Refresh</button>
        </div>
      </div>

      <div class="kpi-row" id="analytics-kpis" style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px;animation:fadeInUp 0.6s ease">
        <div class="card" style="text-align:center;padding:20px"><div class="loader-spinner"></div></div>
        <div class="card" style="text-align:center;padding:20px"><div class="loader-spinner"></div></div>
        <div class="card" style="text-align:center;padding:20px"><div class="loader-spinner"></div></div>
        <div class="card" style="text-align:center;padding:20px"><div class="loader-spinner"></div></div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px" id="analytics-charts">
        <div class="card chart-card"><div class="card-header"><div class="card-title">🎯 Leads by Source</div><span class="chart-badge">distribution</span></div><div style="padding:8px 16px 16px"><canvas id="chart-leads-source" height="240"></canvas></div></div>
        <div class="card chart-card"><div class="card-header"><div class="card-title">🧪 Leads by Stage</div><span class="chart-badge">clinical phase</span></div><div style="padding:8px 16px 16px"><canvas id="chart-leads-stage" height="240"></canvas></div></div>
        <div class="card chart-card" style="grid-column:1/-1"><div class="card-header"><div class="card-title">🔬 Top Therapeutic Focus Areas</div><span class="chart-badge">by lead count</span></div><div style="padding:8px 16px 16px"><canvas id="chart-focus-areas" height="240"></canvas></div></div>
        <div class="card chart-card" style="grid-column:1/-1"><div class="card-header"><div class="card-title">💊 CRO Service Demand</div><span class="chart-badge">most requested</span></div><div style="padding:8px 16px 16px"><canvas id="chart-service-demand" height="220"></canvas></div></div>
        <div class="card chart-card"><div class="card-header"><div class="card-title">💼 Deals by Type</div><span class="chart-badge">M&A · IPO · Funding</span></div><div style="padding:8px 16px 16px"><canvas id="chart-deals-type" height="240"></canvas></div></div>
        <div class="card chart-card"><div class="card-header"><div class="card-title">📰 News by Source</div><span class="chart-badge">coverage</span></div><div style="padding:8px 16px 16px"><canvas id="chart-news-source" height="240"></canvas></div></div>
        <div class="card chart-card" style="grid-column:1/-1"><div class="card-header"><div class="card-title">🔗 LinkedIn Signal Keywords</div><span class="chart-badge">trending topics</span></div><div style="padding:8px 16px 16px"><canvas id="chart-linkedin-keywords" height="200"></canvas></div></div>
      </div>
    `;

    document.getElementById('analytics-refresh-btn')?.addEventListener('click', () => this.loadData());
    await this.loadData();
  },

  async loadData() {
    try {
      const r = await App.apiFetch(`${App.apiBase}/analytics/overview`);
      if (!r.ok) throw new Error(r.statusText || 'Failed to load');
      this.data = await r.json();
    } catch (e) {
      this.data = null;
      document.getElementById('analytics-charts').innerHTML =
        `<div class="empty-state" style="grid-column:1/-1">
          <div class="empty-state-icon">📡</div>
          <div class="empty-state-title">Unable to load analytics</div>
          <div class="empty-state-desc">${e.message}</div>
        </div>`;
      return;
    }

    const updated = document.getElementById('analytics-updated');
    if (updated && this.data.generated) {
      const d = new Date(this.data.generated);
      updated.textContent = `Updated: ${d.toLocaleTimeString()}`;
    }

    this.renderKPIs();
    // Slight delay for KPI render, then charts
    setTimeout(() => this.renderCharts(), 200);
  },

  // ── KPI Cards with animated counters ───────────────────────────────────────
  renderKPIs() {
    const d = this.data;
    if (!d) return;
    const kpis = document.getElementById('analytics-kpis');
    const items = [
      { value: d.totals.leads, label: 'Intelligence Leads', icon: '🎯', color: '#818cf8', glow: 'rgba(129,140,248,0.15)' },
      { value: d.totals.deals, label: 'Active Deals', icon: '💼', color: '#34d399', glow: 'rgba(52,211,153,0.15)' },
      { value: d.totals.news_articles, label: 'News Articles', icon: '📰', color: '#22d3ee', glow: 'rgba(34,211,238,0.15)' },
      { value: d.totals.linkedin_posts, label: 'LinkedIn Signals', icon: '🔗', color: '#fbbf24', glow: 'rgba(251,191,36,0.15)' },
    ];
    kpis.innerHTML = items.map(({ value, label, icon, color, glow }) => `
      <div class="kpi-card-premium" style="--kpi-color:${color};--kpi-glow:${glow}">
        <div class="kpi-icon">${icon}</div>
        <div class="kpi-value" data-target="${value}">0</div>
        <div class="kpi-label">${label}</div>
      </div>
    `).join('');

    // Animate counters
    items.forEach((_, i) => {
      const el = kpis.children[i]?.querySelector('.kpi-value');
      if (!el) return;
      const target = parseInt(el.dataset.target) || 0;
      const duration = 800;
      const start = performance.now();
      const animate = (now) => {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        el.textContent = Math.round(target * eased).toLocaleString();
        if (progress < 1) requestAnimationFrame(animate);
      };
      requestAnimationFrame(animate);
    });
  },

  // ── Chart Rendering ────────────────────────────────────────────────────────
  renderCharts() {
    this.charts.forEach(c => c.destroy());
    this.charts = [];
    const d = this.data;
    if (!d) return;

    // Add CSS animation keyframes for chart cards
    document.querySelectorAll('.chart-card').forEach((card, i) => {
      card.style.animation = `fadeInUp 0.5s ease ${i * 0.08}s both`;
    });

    this._doughnut('chart-leads-source', d.leads.by_source, this.PALETTES.primary);
    this._doughnut('chart-leads-stage', d.leads.by_stage, this.PALETTES.ocean);
    this._luxuryBar('chart-focus-areas', d.leads.top_focus_areas, this.PALETTES.lavender);
    this._luxuryBar('chart-service-demand', d.service_demand, this.PALETTES.forest);
    this._doughnut('chart-deals-type', d.deals.by_type, this.PALETTES.sunset);
    this._luxuryBar('chart-news-source', d.news.by_source, this.PALETTES.ocean);
    if (Object.keys(d.linkedin.top_keywords).length > 0) {
      this._luxuryBar('chart-linkedin-keywords', d.linkedin.top_keywords, this.PALETTES.rose);
    } else {
      const ctx = document.getElementById('chart-linkedin-keywords');
      if (ctx?.parentElement) ctx.parentElement.innerHTML =
        '<div style="text-align:center;padding:40px;color:var(--text-dim);font-size:13px">No LinkedIn keyword data yet — run the aggregator to populate</div>';
    }
  },

  // ── Premium Doughnut ───────────────────────────────────────────────────────
  _doughnut(canvasId, data, palette) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const labels = Object.keys(data);
    const values = Object.values(data);
    if (labels.length === 0) {
      canvas.parentElement.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-dim)">No data available</div>';
      return;
    }
    const total = values.reduce((a, b) => a + b, 0);
    const ctx = canvas.getContext('2d');

    // Build gradient backgrounds
    const bgColors = labels.map((_, i) => {
      const base = palette[i % palette.length];
      return this._createGradient(ctx, [base, this._darken(base, 0.2)], true);
    });

    const chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: bgColors,
          borderColor: 'rgba(15,15,25,0.8)',
          borderWidth: 3,
          hoverBorderColor: 'rgba(255,255,255,0.25)',
          hoverBorderWidth: 3,
          borderRadius: 3,
          spacing: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        animation: { animateScale: true, animateRotate: true, duration: 1200, easing: 'easeOutQuart' },
        plugins: {
          legend: {
            position: 'right',
            labels: {
              color: '#a1a1aa',
              font: { size: 11, family: "'IBM Plex Sans', sans-serif" },
              padding: 14,
              usePointStyle: true,
              pointStyleWidth: 10,
              pointStyleHeight: 10,
              generateLabels: (chart) => {
                const ds = chart.data.datasets[0];
                return chart.data.labels.map((label, i) => ({
                  text: `${label}  (${((ds.data[i] / total) * 100).toFixed(0)}%)`,
                  fillStyle: palette[i % palette.length],
                  strokeStyle: palette[i % palette.length],
                  lineWidth: 0,
                  hidden: false,
                  index: i,
                  pointStyle: 'circle',
                  rotation: 0,
                }));
              },
            },
          },
          tooltip: {
            backgroundColor: 'rgba(20,20,35,0.95)',
            titleFont: { size: 13, family: "'IBM Plex Sans', sans-serif", weight: '600' },
            bodyFont: { size: 12, family: "'IBM Plex Sans', sans-serif" },
            padding: 12,
            cornerRadius: 8,
            displayColors: true,
            boxPadding: 4,
            callbacks: {
              label: (ctx) => `  ${ctx.label}: ${ctx.parsed} leads (${((ctx.parsed / total) * 100).toFixed(1)}%)`,
            },
          },
        },
      },
      plugins: [{
        id: 'centerText',
        afterDraw: (chart) => {
          const { ctx, chartArea: { top, bottom, left, right } } = chart;
          ctx.save();
          ctx.font = "bold 18px 'Space Grotesk', sans-serif";
          ctx.fillStyle = '#e4e4e7';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(total, (left + right) / 2, (top + bottom) / 2 - 6);
          ctx.font = "10px 'IBM Plex Sans', sans-serif";
          ctx.fillStyle = '#71717a';
          ctx.fillText('TOTAL', (left + right) / 2, (top + bottom) / 2 + 14);
          ctx.restore();
        },
      }],
    });
    this.charts.push(chart);
  },

  // ── Luxury Horizontal Bar ──────────────────────────────────────────────────
  _luxuryBar(canvasId, data, palette) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const entries = Object.entries(data);
    if (entries.length === 0) {
      canvas.parentElement.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-dim)">No data available</div>';
      return;
    }
    const labels = entries.map(([k]) => k);
    const values = entries.map(([, v]) => v);
    const maxVal = Math.max(...values);

    const chart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: (ctx) => {
            const { chart } = ctx;
            const { ctx: canvasCtx, chartArea } = chart;
            if (!chartArea) return palette[0];
            const g = canvasCtx.createLinearGradient(chartArea.left, 0, chartArea.right, 0);
            const ratio = values[ctx.dataIndex] / maxVal;
            g.addColorStop(0, palette[0]);
            g.addColorStop(ratio, palette[Math.min(2, palette.length - 1)]);
            g.addColorStop(1, palette[palette.length - 1]);
            return g;
          },
          borderRadius: 6,
          borderSkipped: false,
          barThickness: 18,
          borderColor: 'transparent',
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 1000, easing: 'easeOutQuart' },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(20,20,35,0.95)',
            titleFont: { size: 12, family: "'IBM Plex Sans', sans-serif", weight: '600' },
            bodyFont: { size: 12, family: "'IBM Plex Sans', sans-serif" },
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              label: (ctx) => `  ${ctx.raw} ${ctx.raw === 1 ? 'item' : 'items'}`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: '#52525b', font: { size: 10, family: "'IBM Plex Mono', monospace" }, padding: 4 },
            grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
            border: { display: false },
          },
          y: {
            ticks: { color: '#a1a1aa', font: { size: 11, family: "'IBM Plex Sans', sans-serif" }, padding: 8 },
            grid: { display: false },
            border: { display: false },
          },
        },
      },
      plugins: [{
        id: 'valueLabels',
        afterDatasetsDraw: (chart) => {
          const { ctx } = chart;
          chart.data.datasets[0].data.forEach((value, i) => {
            const meta = chart.getDatasetMeta(0);
            const { x, y } = meta.data[i];
            ctx.save();
            ctx.font = "600 11px 'IBM Plex Mono', monospace";
            ctx.fillStyle = '#e4e4e7';
            ctx.textAlign = 'left';
            ctx.textBaseline = 'middle';
            ctx.fillText(value, x + 8, y);
            ctx.restore();
          });
        },
      }],
    });
    this.charts.push(chart);
  },

  // ── Utils ──────────────────────────────────────────────────────────────────
  _darken(hex, amount) {
    const num = parseInt(hex.replace('#', ''), 16);
    const r = Math.max(0, (num >> 16) - Math.round(255 * amount));
    const g = Math.max(0, ((num >> 8) & 0x00FF) - Math.round(255 * amount));
    const b = Math.max(0, (num & 0x0000FF) - Math.round(255 * amount));
    return `rgb(${r},${g},${b})`;
  },
};
