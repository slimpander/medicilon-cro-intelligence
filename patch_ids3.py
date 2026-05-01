import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Check news panel CSS in original style block
idx = html.find('#news-panel')
while idx != -1:
    chunk = html[max(0,idx-5):idx+200]
    if '{' in chunk or 'display' in chunk:
        print("CSS:", chunk[:200])
        print("---")
    idx = html.find('#news-panel', idx+1)

# check openNewsPanel function
idx2 = html.find('function openNewsPanel')
if idx2 != -1:
    print("openNewsPanel fn:", html[idx2:idx2+200])

# Check if duplicate news panel exists (2 occurrences of id="news-panel")
count = html.count('id="news-panel"')
print(f"\nid=news-panel occurrences: {count}")
