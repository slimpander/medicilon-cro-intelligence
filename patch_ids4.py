import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Check for duplicate CSS blocks we may have injected
dup_css_marker = '/* -- News Panel --'
count1 = html.count('/* ── News Panel')
count2 = html.count('/* -- News Panel')
print(f"News panel CSS blocks (em-dash): {count1}")
print(f"News panel CSS blocks (dash): {count2}")

# Check for duplicate modal overlay
count3 = html.count('id="cro-modal-overlay"')
print(f"cro-modal-overlay occurrences: {count3}")

# Check for duplicate NEWS_DATA
count4 = html.count('const NEWS_DATA')
print(f"NEWS_DATA definitions: {count4}")

# Check if our extra CSS block is causing issues (extra #news-panel rules with display:none/.visible)
count5 = html.count('#news-panel {')
print(f"#news-panel CSS rules: {count5}")

# Find any .visible CSS
if '.visible' in html:
    idx = html.find('.visible')
    print("First .visible CSS:", html[max(0,idx-50):idx+100])

# Check the cro-modal JS is correctly wired
print("\nopenCroModal calls:", html.count('openCroModal'))
print("cro-modal-overlay in HTML:", html.count('id="cro-modal-overlay"'))
print("renderStrategyPanel calls:", html.count('renderStrategyPanel'))
