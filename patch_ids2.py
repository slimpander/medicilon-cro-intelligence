import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find what IDs exist in news panel
idx = html.find('id="news-panel"')
if idx != -1:
    chunk = html[idx:idx+600]
    print("News panel HTML:")
    print(chunk)
