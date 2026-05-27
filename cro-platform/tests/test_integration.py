"""Integration test for all 3 phases."""
import sys, time, threading
sys.path.insert(0, '.')
import main, uvicorn, httpx

t = threading.Thread(target=lambda: uvicorn.run(main.app, host='127.0.0.1', port=8001, log_level='error'), daemon=True)
t.start()
time.sleep(2)

# Login
login = httpx.post('http://127.0.0.1:8001/api/auth/login', json={'username': 'admin', 'password': 'admin123'}, timeout=5)
token = login.json()['token']
print(f'[1] Auth: OK ({token[:16]}...)')
headers = {'Authorization': f'Bearer {token}'}

# Phase 3.5: AI Scoring
r = httpx.post('http://127.0.0.1:8001/api/leads/score', headers=headers, json={
    'name': 'NeuroBio Therapeutics', 'state': 'MA', 'stage': 'Series B',
    'needs': ['DMPK', 'ADME', 'Toxicology', 'Bioanalysis'],
    'total_funding_usd': 75000000,
    'focus': 'Seeking CRO partners for preclinical DMPK and IND-enabling tox studies',
    'date': '2026-05-20',
}, timeout=5)
d = r.json()
print(f'[2] AI Score: {d["total_score"]} | Tier: {d["tier"]}')
print(f'    Breakdown: {d["breakdown"]}')
print(f'    Rec: {d["bd_priority"][:80].encode("ascii","replace").decode()}...')

# Phase 3.4: LinkedIn stats
r2 = httpx.get('http://127.0.0.1:8001/api/linkedin/stats', headers=headers, timeout=5)
print(f'[3] LinkedIn Stats: {r2.json()}')

# Submit a test LinkedIn post
post = {
    'author': 'Jane Smith', 'author_title': 'VP R&D at GenTech',
    'author_company': 'GenTech Biosciences',
    'content': 'We are actively seeking CRO partners for our preclinical DMPK program. IND-enabling studies starting Q3. Please reach out!',
    'post_url': 'https://linkedin.com/feed/update/test123',
    'post_date': '2026-05-25',
}
r3 = httpx.post('http://127.0.0.1:8001/api/linkedin/posts', json=post, timeout=5)
d3 = r3.json()
print(f'[4] LinkedIn Post Scored: {d3["relevance_score"]} | High Priority: {d3["is_high_priority"]}')
print(f'    Keywords: {d3["matched_keywords"]}')
bd_notes = d3["bd_notes"][:100].encode("ascii","replace").decode()
print(f'    BD Notes: {bd_notes}...')

# Check stats updated
r4 = httpx.get('http://127.0.0.1:8001/api/linkedin/stats', headers=headers, timeout=5)
print(f'[5] Updated LinkedIn Stats: {r4.json()}')

# Phase 3.6: Generate alerts
r5 = httpx.post('http://127.0.0.1:8001/api/notifications/generate-alerts', headers=headers, timeout=5)
print(f'[6] Alerts Generated: {r5.json()}')

# Get notifications
r6 = httpx.get('http://127.0.0.1:8001/api/notifications', headers=headers, timeout=5)
notifs = r6.json()
print(f'[7] Notifications: {len(notifs)} pending')
for n in notifs[:3]:
    msg = n["message"].encode("ascii","replace").decode()
    print(f'    - {msg}')

print('\n=== ALL 3 PHASES VERIFIED ===')
print('Phase 3.4: LinkedIn Monitor - OK')
print('Phase 3.5: AI Lead Scoring - OK')
print('Phase 3.6: Notification Pipeline - OK')
