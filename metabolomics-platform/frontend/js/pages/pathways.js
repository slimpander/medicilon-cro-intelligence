/**
 * Pathways Page Controller
 */

document.getElementById('btn-run-pathways').addEventListener('click', async () => {
    const btn = document.getElementById('btn-run-pathways');
    btn.disabled = true;
    btn.textContent = 'Running...';
    
    try {
        const result = await apiPost('/api/stats/pathway', { database: 'KEGG' });
        
        let html = '';
        result.pathways.forEach((p, i) => {
            const sig = p.q_value < 0.05;
            html += `
                <div class="pathway-card">
                    <div class="pathway-rank" style="background:${sig ? '#3fb950' : '#8b949e'}">${i+1}</div>
                    <div class="pathway-info">
                        <div class="pathway-name">${p.name}</div>
                        <div class="pathway-meta">${p.hits}/${p.matched} hits in pathway (${p.total} total metabolites)</div>
                    </div>
                    <div class="pathway-stats">
                        <div class="pathway-er">${p.enrichment_ratio}x</div>
                        <div class="pathway-pval">p=${p.p_value.toFixed(4)} q=${p.q_value.toFixed(4)}</div>
                    </div>
                </div>
            `;
        });
        
        if (!html) html = '<p style="color: var(--text-secondary)">No enriched pathways found. Try running the pipeline with more features.</p>';
        document.getElementById('pathways-list').innerHTML = html;
        document.getElementById('pathways-results-card').style.display = 'block';
        
    } catch (e) {
        document.getElementById('pathways-list').innerHTML = `<p style="color:#dc2626">Error: ${e.message}</p>`;
    }
    btn.disabled = false;
    btn.textContent = 'Run Pathway Enrichment';
});
