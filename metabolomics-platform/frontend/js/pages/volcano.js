/**
 * Volcano Page Controller
 */

let volcanoChart = null;

function initVolcanoChart() {}

document.getElementById('btn-run-volcano').addEventListener('click', async () => {
    const btn = document.getElementById('btn-run-volcano');
    btn.disabled = true;
    btn.textContent = 'Running...';
    
    try {
        const params = {
            group_a_indices: [0, 1, 2],
            group_b_indices: [3, 4, 5],
            fold_change_threshold: parseFloat(document.getElementById('volc-fc').value),
            p_value_threshold: parseFloat(document.getElementById('volc-pval').value),
            test_method: document.getElementById('volc-test').value,
        };
        const result = await apiPost('/api/stats/volcano', params);
        
        // Info sidebar
        document.getElementById('volcano-info').innerHTML = `
            <h4>${result.group_a} vs ${result.group_b}</h4>
            <p style="color:#dc2626;font-weight:550"><b>Up:</b> ${result.n_upregulated}</p>
            <p style="color:#16a34a;font-weight:550"><b>Down:</b> ${result.n_downregulated}</p>
            <p style="color:#64748b"><b>NS:</b> ${result.features.length - result.n_significant}</p>
            <p style="margin-top:8px"><b>Significant:</b> ${result.n_significant}</p>
        `;
        
        // Build chart data
        const nsPoints = []; // not significant
        const upPoints = []; // upregulated
        const downPoints = []; // downregulated
        
        result.features.forEach(f => {
            const pt = { x: f.log2_fc, y: -Math.log10(Math.max(f.q_value, 1e-15)) };
            if (f.direction === 'up') upPoints.push(pt);
            else if (f.direction === 'down') downPoints.push(pt);
            else nsPoints.push(pt);
        });
        
        const ctx = document.getElementById('volcano-chart').getContext('2d');
        if (volcanoChart) volcanoChart.destroy();
        
        const fcThresh = parseFloat(document.getElementById('volc-fc').value);
        const pThresh = -Math.log10(parseFloat(document.getElementById('volc-pval').value));
        
        volcanoChart = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [
                    {
                        label: 'Not Significant',
                        data: nsPoints,
                        backgroundColor: 'rgba(148, 163, 184, 0.45)',
                        pointRadius: 3,
                    },
                    {
                        label: 'Upregulated',
                        data: upPoints,
                        backgroundColor: 'rgba(220, 38, 38, 0.6)',
                        pointRadius: 4,
                    },
                    {
                        label: 'Downregulated',
                        data: downPoints,
                        backgroundColor: 'rgba(22, 163, 74, 0.6)',
                        pointRadius: 4,
                    },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Volcano Plot', color: '#1e293b', font: { size: 14 } },
                    legend: { labels: { color: '#1e293b' } },
                    annotation: {
                        annotations: {
                            vline1: {
                                type: 'line', xMin: fcThresh, xMax: fcThresh,
                                borderColor: 'rgba(139, 148, 158, 0.3)', borderWidth: 1, borderDash: [5, 5],
                            },
                            vline2: {
                                type: 'line', xMin: -fcThresh, xMax: -fcThresh,
                                borderColor: 'rgba(139, 148, 158, 0.3)', borderWidth: 1, borderDash: [5, 5],
                            },
                            hline: {
                                type: 'line', yMin: pThresh, yMax: pThresh,
                                borderColor: 'rgba(139, 148, 158, 0.3)', borderWidth: 1, borderDash: [5, 5],
                            },
                        },
                    },
                },
                scales: {
                    x: { 
                        title: { display: true, text: 'log2 Fold Change', color: '#8b949e' },
                        grid: { color: '#30363d' }, ticks: { color: '#8b949e' },
                    },
                    y: { 
                        title: { display: true, text: '-log10(q-value)', color: '#8b949e' },
                        grid: { color: '#30363d' }, ticks: { color: '#8b949e' },
                    },
                },
            },
        });
        
    } catch (e) {
        document.getElementById('volcano-info').innerHTML = `<p style="color:#f85149">Error: ${e.message}</p>`;
    }
    btn.disabled = false;
    btn.textContent = 'Run Volcano';
});
