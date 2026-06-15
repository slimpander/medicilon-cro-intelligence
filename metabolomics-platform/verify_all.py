"""Full end-to-end verification for metabolomics platform."""
import urllib.request, json, subprocess, sys

BASE = 'http://localhost:8002'
ok = 0

def check(name, test_fn):
    global ok
    try:
        test_fn()
        ok += 1
        print(f'  [OK] {name}')
    except Exception as e:
        print(f'  [FAIL] {name}: {e}')

# 1. Health
check('Health', lambda: (
    (d := json.loads(urllib.request.urlopen(f'{BASE}/api/health').read())),
    None if d['status'] == 'ok' else (_ for _ in ()).throw(AssertionError('status != ok'))
)[1] if False else None)
# Simpler version
d = json.loads(urllib.request.urlopen(f'{BASE}/api/health').read())
assert d['status'] == 'ok'
ok += 1
print('  [OK] Health')

# 2. Pipeline
data = json.dumps({'generate_synthetic': True, 'n_synthetic_metabolites': 6, 'n_synthetic_scans': 200}).encode()
req = urllib.request.Request(f'{BASE}/api/pipeline/run', data=data, headers={'Content-Type': 'application/json'})
d = json.loads(urllib.request.urlopen(req).read())
assert d.get('grouped_features', -1) >= 0
assert len(d.get('alignment', [])) == 3
ok += 1
print(f'  [OK] Pipeline: {d["grouped_features"]} features, {len(d["alignment"])} alignments')

# 3. PCA
data = json.dumps({'n_components': 2, 'scale': 'pareto'}).encode()
req = urllib.request.Request(f'{BASE}/api/stats/pca', data=data, headers={'Content-Type': 'application/json'})
d = json.loads(urllib.request.urlopen(req).read())
assert d['n_components'] >= 1
ok += 1
print(f'  [OK] PCA: {d["n_components"]} components, PC1={d["variance_explained"][0]*100:.1f}%')

# 4. Volcano
data = json.dumps({'group_a_indices': [0], 'group_b_indices': [1,2], 'fold_change_threshold': 0.5, 'p_value_threshold': 0.1}).encode()
req = urllib.request.Request(f'{BASE}/api/stats/volcano', data=data, headers={'Content-Type': 'application/json'})
d = json.loads(urllib.request.urlopen(req).read())
assert d['n_significant'] >= 0
ok += 1
print(f'  [OK] Volcano: {d["n_significant"]} sig, {d["n_upregulated"]} up, {d["n_downregulated"]} down')

# 5. Annotation
req = urllib.request.Request(f'{BASE}/api/annotate', data=json.dumps({'mass_tolerance_ppm': 10, 'use_online': False}).encode(), headers={'Content-Type': 'application/json'})
d = json.loads(urllib.request.urlopen(req).read())
assert d['total'] >= 1
ok += 1
print(f'  [OK] Annotation: {d["annotated"]}/{d["total"]} annotated')

# 6. Pathways
req = urllib.request.Request(f'{BASE}/api/stats/pathway', data=json.dumps({}).encode(), headers={'Content-Type': 'application/json'})
d = json.loads(urllib.request.urlopen(req).read())
ok += 1
print(f'  [OK] Pathways: {len(d["pathways"])} pathways')

# 7. CSV export
resp = urllib.request.urlopen(f'{BASE}/api/export/csv')
content = resp.read().decode()
assert 'feature_id' in content
ok += 1
print(f'  [OK] CSV Export: {len(content.splitlines())} lines')

# 8. Web UI
resp = urllib.request.urlopen(f'{BASE}/')
html = resp.read().decode().lower()
assert 'metabolomics' in html
assert 'chart.js' in html
ok += 1
print(f'  [OK] Web UI: {len(html)} bytes, has Chart.js')

# 9. Phase 1 tests
r = subprocess.run(['python', 'test_phase1.py'], capture_output=True, text=True)
assert '7/7 passed' in r.stdout, f'Expected 7/7, got: {r.stdout[-300:]}'
ok += 1
print('  [OK] Phase 1 tests: 7/7')

# 10. Phase 2 tests
r = subprocess.run(['python', 'test_phase2.py'], capture_output=True, text=True)
assert '13/13 passed' in r.stdout, f'Expected 13/13, got: {r.stdout[-300:]}'
ok += 1
print('  [OK] Phase 2 tests: 13/13')

print(f'\n  ALL {ok}/10 VERIFICATIONS PASSED')
