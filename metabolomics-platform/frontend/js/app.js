/**
 * Metabolomics Platform v0.2.0 — Main App Controller
 */

const API_BASE = '';

// Navigation
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        const page = item.dataset.page;
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById('page-' + page).classList.add('active');
        
        // Initialize charts when navigating to stats/volcano pages
        if (page === 'stats') initStatsCharts();
        if (page === 'volcano') initVolcanoChart();
    });
});

// API helpers
async function apiGet(path) {
    const resp = await fetch(API_BASE + path);
    if (!resp.ok) throw new Error(await resp.text());
    return resp.json();
}

async function apiPost(path, data) {
    const resp = await fetch(API_BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'API error');
    }
    return resp.json();
}

// Status indicator
async function checkHealth() {
    try {
        const h = await apiGet('/api/health');
        const dot = document.querySelector('.status-dot');
        dot.className = 'status-dot online';
        document.getElementById('status-text').textContent = 'Server online';
    } catch (e) {
        const dot = document.querySelector('.status-dot');
        dot.className = 'status-dot offline';
        document.getElementById('status-text').textContent = 'Server offline';
    }
}

// Chart.js light theme defaults
Chart.defaults.color = '#64748b';
Chart.defaults.borderColor = '#e2e8f0';
Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
Chart.defaults.font.size = 11;

// Stats helper
function makeStatCard(value, label, colorClass = '') {
    return `<div class="stat-card ${colorClass}">
        <div class="stat-value">${value}</div>
        <div class="stat-label">${label}</div>
    </div>`;
}

// Init
checkHealth();
setInterval(checkHealth, 30000);
