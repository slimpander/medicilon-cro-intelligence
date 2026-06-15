/**
 * Annotation Page Controller
 */

document.getElementById('btn-run-annotation').addEventListener('click', async () => {
    const btn = document.getElementById('btn-run-annotation');
    btn.disabled = true;
    btn.textContent = 'Annotating...';
    
    try {
        const params = {
            mass_tolerance_ppm: parseFloat(document.getElementById('anno-ppm').value),
            mode: document.getElementById('anno-mode').value,
            use_online: document.getElementById('anno-online').checked,
            max_matches: 5,
        };
        const result = await apiPost('/api/annotate', params);
        
        // Online lookup status — distinguish "no match" from "lookup unavailable"
        const statusEl = document.getElementById('annotation-online-status');
        if (result.online_requested) {
            if (result.online_available) {
                statusEl.style.display = 'block';
                statusEl.style.background = '#dcfce7';
                statusEl.style.color = '#166534';
                statusEl.textContent = `Online databases returned matches: ${result.databases_with_hits.join(', ')}.`;
            } else {
                statusEl.style.display = 'block';
                statusEl.style.background = '#fef3c7';
                statusEl.style.color = '#92400e';
                const why = (result.online_errors && result.online_errors.length)
                    ? ' Details: ' + result.online_errors.join('; ')
                    : ' (no records returned — these databases usually need a license/API key).';
                statusEl.textContent = 'Online lookup unavailable; showing curated offline matches only.' + why;
            }
        } else {
            statusEl.style.display = 'none';
        }

        // Stats
        document.getElementById('annotation-stats').innerHTML =
            makeStatCard(result.total, 'Total Features') +
            makeStatCard(result.annotated, 'Annotated', 'green') +
            makeStatCard(result.high_confidence, 'High Confidence', 'green');
        
        // Table
        const tbody = document.querySelector('#annotation-table tbody');
        tbody.innerHTML = '';
        result.features.forEach(f => {
            if (f.top_match) {
                const m = f.top_match;
                const row = tbody.insertRow();
                row.insertCell().textContent = f.mz;
                row.insertCell().textContent = f.rt;
                row.insertCell().innerHTML = `<b>${m.name}</b>`;
                row.insertCell().textContent = m.formula;
                row.insertCell().textContent = m.adduct || '-';
                row.insertCell().innerHTML = `<span style="color:${m.mass_error_ppm < 5 ? '#16a34a' : '#ea580c'}">${m.mass_error_ppm.toFixed(1)}</span>`;
                row.insertCell().innerHTML = `<span style="color:${m.score >= 0.7 ? '#16a34a' : '#64748b'}">${m.score.toFixed(3)}</span>`;
                row.insertCell().textContent = m.database;
                row.style.cursor = 'pointer';
                row.title = f.all_matches.map(m => `${m.name} (${m.database}, ${m.mass_error_ppm}ppm)`).join('\n');
            } else {
                const row = tbody.insertRow();
                row.insertCell().textContent = f.mz;
                row.insertCell().textContent = f.rt;
                row.insertCell().textContent = 'Unknown';
                row.insertCell().textContent = '-';
                row.insertCell().textContent = '-';
                row.insertCell().textContent = '-';
                row.insertCell().textContent = '-';
                row.insertCell().textContent = '-';
                row.style.opacity = '0.5';
            }
        });
        
        document.getElementById('annotation-results-card').style.display = 'block';
        
    } catch (e) {
        alert('Error: ' + e.message);
    }
    btn.disabled = false;
    btn.textContent = 'Annotate Features';
});
