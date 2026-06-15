/**
 * Stats Page Controller — PCA + PLS-DA
 */

let pcaChart = null;
let plsdaChart = null;

function initStatsCharts() {
    // placeholder canvases
}

// PCA
document.getElementById('btn-run-pca').addEventListener('click', async () => {
    const btn = document.getElementById('btn-run-pca');
    btn.disabled = true;
    btn.textContent = 'Running...';
    
    try {
        const params = {
            n_components: parseInt(document.getElementById('pca-components').value),
            scale: document.getElementById('pca-scale').value,
        };
        const result = await apiPost('/api/stats/pca', params);
        
        // Info sidebar
        let infoHtml = '<h4>Variance Explained</h4>';
        result.variance_explained.forEach((v, i) => {
            infoHtml += `<p>PC${i+1}: ${(v*100).toFixed(1)}%</p>`;
        });
        infoHtml += `<p style="margin-top:8px"><b>Cumulative:</b> ${(result.cumulative_variance[result.cumulative_variance.length-1]*100).toFixed(1)}%</p>`;
        document.getElementById('pca-info').innerHTML = infoHtml;
        
        // Scores chart
        const ctx = document.getElementById('pca-scores-chart').getContext('2d');
        if (pcaChart) pcaChart.destroy();
        
        const colors = ['#2563eb', '#16a34a', '#ea580c', '#dc2626', '#8b5cf6', '#0891b2'];
        const datasets = [];
        
        result.scores.forEach((sample, i) => {
            datasets.push({
                label: result.sample_names[i] || `Sample ${i+1}`,
                data: [{x: sample[0], y: sample[1] || 0}],
                backgroundColor: colors[i % colors.length],
                borderColor: colors[i % colors.length],
                pointRadius: 8, pointHoverRadius: 12,
            });
        });
        
        pcaChart = new Chart(ctx, {
            type: 'scatter',
            data: { datasets },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'PCA Scores Plot', color: '#1e293b', font: { size: 14 } },
                    legend: { labels: { color: '#1e293b' } },
                },
                scales: {
                    x: { 
                        title: { display: true, text: `PC1 (${(result.variance_explained[0]*100).toFixed(1)}%)`, color: '#8b949e' },
                        grid: { color: '#30363d' }, ticks: { color: '#8b949e' },
                    },
                    y: { 
                        title: { display: true, text: `PC2 (${(result.variance_explained[1]*100).toFixed(1)}%)`, color: '#8b949e' },
                        grid: { color: '#30363d' }, ticks: { color: '#8b949e' },
                    },
                },
            },
        });
        
    } catch (e) {
        document.getElementById('pca-info').innerHTML = `<p style="color:#f85149">Error: ${e.message}</p>`;
    }
    btn.disabled = false;
    btn.textContent = 'Run PCA';
});

// PLS-DA
document.getElementById('btn-run-plsda').addEventListener('click', async () => {
    const btn = document.getElementById('btn-run-plsda');
    btn.disabled = true;
    btn.textContent = 'Running...';
    
    try {
        const rawLabels = document.getElementById('plsda-labels').value.trim();
        if (!rawLabels) {
            // Auto-generate if empty: split samples into two groups
            if (window._pipelineSampleCount && window._pipelineSampleCount >= 2) {
                const half = Math.floor(window._pipelineSampleCount / 2);
                const labels = [];
                for (let i = 0; i < window._pipelineSampleCount; i++) {
                    labels.push(i < half ? 'GroupA' : 'GroupB');
                }
                document.getElementById('plsda-labels').value = labels.join(',');
                document.getElementById('plsda-label-hint').textContent = 
                    `Auto-generated ${window._pipelineSampleCount} labels: ${labels.join(', ')}`;
            } else {
                throw new Error('Run pipeline first, then enter group labels');
            }
        }
        
        const labels = document.getElementById('plsda-labels').value.split(',').map(s => s.trim());
        
        if (window._pipelineSampleCount && labels.length !== window._pipelineSampleCount) {
            throw new Error(
                `Label count (${labels.length}) must match sample count (${window._pipelineSampleCount}). ` +
                `Samples: ${window._pipelineSampleNames?.join(', ') || 'unknown'}`
            );
        }
        
        const params = {
            n_components: 2,
            group_labels: labels,
        };
        const result = await apiPost('/api/stats/plsda', params);
        
        // Info sidebar
        let infoHtml = '<h4>Model Diagnostics</h4>';
        result.r2x.forEach((v, i) => {
            infoHtml += `<p>R²X Comp${i+1}: ${(v*100).toFixed(1)}%</p>`;
        });
        result.r2y.forEach((v, i) => {
            infoHtml += `<p>R²Y Comp${i+1}: ${(v*100).toFixed(1)}%</p>`;
        });
        infoHtml += `<p style="margin-top:8px"><b>Classes:</b> ${result.class_labels.join(', ')}</p>`;
        document.getElementById('plsda-info').innerHTML = infoHtml;
        
        // Scores chart
        const ctx = document.getElementById('plsda-scores-chart').getContext('2d');
        if (plsdaChart) plsdaChart.destroy();
        
        const colors = ['#2563eb', '#dc2626', '#16a34a', '#ea580c', '#8b5cf6', '#0891b2'];
        const classColors = {};
        result.class_labels.forEach((c, i) => { classColors[c] = colors[i % colors.length]; });
        
        const datasets = [];
        labels.forEach((label, i) => {
            if (i >= result.scores.length) return;
            datasets.push({
                label: label,
                data: [{x: result.scores[i][0], y: result.scores[i][1] || 0}],
                backgroundColor: classColors[label] || colors[i % colors.length],
                borderColor: classColors[label] || colors[i % colors.length],
                pointRadius: 8, pointHoverRadius: 12,
            });
        });
        
        plsdaChart = new Chart(ctx, {
            type: 'scatter',
            data: { datasets },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'PLS-DA Scores Plot', color: '#1e293b', font: { size: 14 } },
                    legend: { labels: { color: '#1e293b' } },
                },
                scales: {
                    x: { 
                        title: { display: true, text: 'LV1', color: '#8b949e' },
                        grid: { color: '#30363d' }, ticks: { color: '#8b949e' },
                    },
                    y: { 
                        title: { display: true, text: 'LV2', color: '#8b949e' },
                        grid: { color: '#30363d' }, ticks: { color: '#8b949e' },
                    },
                },
            },
        });
        
    } catch (e) {
        document.getElementById('plsda-info').innerHTML = `<p style="color:#f85149">Error: ${e.message}</p>`;
    }
    btn.disabled = false;
    btn.textContent = 'Run PLS-DA';
});
