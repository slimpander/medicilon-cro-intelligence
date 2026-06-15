/**
 * Pipeline Page Controller v0.3.0
 * Supports: synthetic data, real mzML files, batch multi-file processing
 */

// Data source toggle
document.querySelectorAll('input[name="data-source"]').forEach(radio => {
    radio.addEventListener('change', () => {
        const isReal = radio.value === 'real';
        document.getElementById('file-section').style.display = isReal ? 'block' : 'none';
        refreshFileList();
    });
});

// File upload
document.getElementById('btn-upload').addEventListener('click', () => {
    document.getElementById('mzml-upload').click();
});

document.getElementById('mzml-upload').addEventListener('change', async (e) => {
    const files = e.target.files;
    if (!files.length) return;
    const status = document.getElementById('upload-status');
    
    for (const file of files) {
        status.textContent = `Uploading ${file.name}...`;
        try {
            const form = new FormData();
            form.append('file', file);
            await fetch('/api/upload', { method: 'POST', body: form });
        } catch (err) {
            status.textContent = `Upload failed: ${file.name}`;
            return;
        }
    }
    status.textContent = `Uploaded ${files.length} file(s)`;
    refreshFileList();
    e.target.value = '';
});

// Refresh file list
async function refreshFileList() {
    if (document.querySelector('input[name="data-source"]:checked').value !== 'real') return;
    
    const container = document.getElementById('file-list');
    try {
        const data = await apiGet('/api/files');
        if (!data.files.length) {
            container.innerHTML = '<span style="color:var(--text-muted)">No files uploaded. Upload mzML files above.</span>';
            return;
        }
        
        let html = '<table style="width:100%;font-size:0.85rem"><thead><tr><th></th><th>File</th><th>Size</th><th></th></tr></thead><tbody>';
        data.files.forEach(f => {
            html += `<tr>
                <td><input type="checkbox" class="file-select" value="${f.name}"></td>
                <td>${f.name}</td>
                <td>${f.size_mb} MB</td>
                <td><button class="btn-small btn-danger file-delete" data-file="${f.name}">×</button></td>
            </tr>`;
        });
        html += '</tbody></table>';
        container.innerHTML = html;
        
        // Delete buttons
        document.querySelectorAll('.file-delete').forEach(btn => {
            btn.addEventListener('click', async () => {
                await fetch(`/api/files/${btn.dataset.file}`, { method: 'DELETE' });
                refreshFileList();
            });
        });
        
        // Show/hide batch labels based on selection count
        document.querySelectorAll('.file-select').forEach(cb => {
            cb.addEventListener('change', updateBatchUI);
        });
        updateBatchUI();
        
    } catch (e) {
        container.innerHTML = '<span style="color:var(--danger)">Failed to load file list</span>';
    }
}

function updateBatchUI() {
    const selected = document.querySelectorAll('.file-select:checked');
    const labelsRow = document.getElementById('batch-labels-row');
    const labelsInput = document.getElementById('batch-labels');
    
    if (selected.length > 1) {
        labelsRow.hidden = false;
        // Auto-fill labels from filenames if empty
        if (!labelsInput.value) {
            labelsInput.value = Array.from(selected).map(cb => cb.value.replace('.mzML','').replace('.mzml','')).join(',');
        }
    } else {
        labelsRow.hidden = true;
    }
}

// Run pipeline
document.getElementById('btn-run-pipeline').addEventListener('click', async () => {
    const btn = document.getElementById('btn-run-pipeline');
    const status = document.getElementById('pipeline-status');
    const dot = document.querySelector('.status-dot');
    
    btn.disabled = true;
    dot.className = 'status-dot busy';
    
    const isReal = document.querySelector('input[name="data-source"]:checked').value === 'real';
    
    try {
        const params = {
            generate_synthetic: !isReal,
            snr_threshold: parseFloat(document.getElementById('param-snr').value),
            min_intensity: parseFloat(document.getElementById('param-minint').value),
            peak_width_min: parseFloat(document.getElementById('param-pwmin').value),
            peak_width_max: parseFloat(document.getElementById('param-pwmax').value),
            mz_tolerance_da: parseFloat(document.getElementById('param-mztol').value),
            min_scans: parseInt(document.getElementById('param-minscans').value),
            mz_bandwidth_ppm: parseFloat(document.getElementById('param-mzbw').value),
            rt_bandwidth_sec: parseFloat(document.getElementById('param-rtbw').value),
            n_synthetic_metabolites: parseInt(document.getElementById('param-nmet').value),
            n_synthetic_scans: parseInt(document.getElementById('param-nscans').value),
        };
        
        if (isReal) {
            const selected = document.querySelectorAll('.file-select:checked');
            if (!selected.length) {
                status.textContent = 'Please select at least one file';
                btn.disabled = false;
                dot.className = 'status-dot offline';
                return;
            }
            params.filenames = Array.from(selected).map(cb => cb.value);
            params.generate_synthetic = false;
            
            // Group labels for multi-file
            const labelsStr = document.getElementById('batch-labels').value.trim();
            if (labelsStr && params.filenames.length > 1) {
                params.group_labels = labelsStr.split(',').map(s => s.trim());
            }
        }
        
        status.textContent = isReal ? 'Processing mzML files...' : 'Generating synthetic data...';
        
        const result = await apiPost('/api/pipeline/run', params);
        
        // Show stats
        const rep = result.replicates[0] || {};
        document.getElementById('pipeline-stats').innerHTML = 
            makeStatCard(rep.total_peaks || 0, 'Total Peaks') +
            makeStatCard(rep.rois || 0, 'ROIs', 'green') +
            makeStatCard(rep.features || 0, 'Features', 'green') +
            makeStatCard(result.grouped_features, 'Grouped', 'orange') +
            makeStatCard(result.n_samples, 'Samples') +
            makeStatCard(result.missing_pct + '%', 'Missing', 'red');
        
        // Alignment table
        if (result.alignment && result.alignment.length) {
            let alHtml = '<table><thead><tr><th>Sample</th><th>Landmarks</th><th>Shift Median</th><th>Shift Max</th></tr></thead><tbody>';
            result.alignment.forEach(a => {
                alHtml += `<tr><td>${a.sample}</td><td>${a.landmarks}</td><td>${a.shift_median}s</td><td>${a.shift_max}s</td></tr>`;
            });
            alHtml += '</tbody></table>';
            document.getElementById('alignment-table').innerHTML = alHtml;
        } else {
            document.getElementById('alignment-table').innerHTML = '<p style="color:var(--text-muted)">Single sample — alignment skipped</p>';
        }
        
        // Features table - dynamic columns based on sample count
        const tbody = document.querySelector('#features-table tbody');
        const thead = document.querySelector('#features-table thead tr');
        tbody.innerHTML = '';
        
        // Update header
        let headerHtml = '<th>ID</th><th>m/z</th><th>RT (s)</th>';
        result.sample_names.forEach(n => headerHtml += `<th>${n}</th>`);
        headerHtml += '<th>Quality</th>';
        thead.innerHTML = headerHtml;
        
        result.top_features.forEach(f => {
            const row = tbody.insertRow();
            row.insertCell().textContent = f.id;
            row.insertCell().textContent = f.mz;
            row.insertCell().textContent = f.rt;
            f.intensities.forEach(v => {
                const cell = row.insertCell();
                cell.textContent = Math.round(v);
            });
            row.insertCell().textContent = f.quality;
        });
        
        // Persistent data-source badge — make synthetic vs. real unmistakable
        const badge = document.getElementById('pipeline-source-badge');
        if (badge) {
            const src = result.data_source || 'synthetic';
            const isSynthetic = src === 'synthetic';
            badge.style.display = 'inline-block';
            badge.style.background = isSynthetic ? '#fef3c7' : '#dcfce7';
            badge.style.color = isSynthetic ? '#92400e' : '#166534';
            badge.textContent = isSynthetic
                ? '⚠ SYNTHETIC DEMO DATA — not real measurements'
                : 'REAL DATA · ' + src;
        }

        document.getElementById('pipeline-results-card').style.display = 'block';
        status.textContent = isReal 
            ? `Completed: ${result.grouped_features} features from ${result.n_samples} file(s)` 
            : 'Pipeline completed (synthetic).';
        dot.className = 'status-dot online';
        
        // Update PLS-DA label hint
        const hint = document.getElementById('plsda-label-hint');
        if (hint) {
            hint.textContent = `Pipeline has ${result.n_samples} samples: ${result.sample_names.join(', ')}`;
        }
        window._pipelineSampleNames = result.sample_names;
        window._pipelineSampleCount = result.n_samples;
        
    } catch (e) {
        status.textContent = 'Error: ' + e.message;
        dot.className = 'status-dot offline';
    }
    btn.disabled = false;
});

// Init
refreshFileList();
