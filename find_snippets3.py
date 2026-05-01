import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

out = []

# Find company legend
idx = html.find('stateCount')
while idx != -1:
    chunk = html[max(0,idx-200):idx+400]
    out.append("=== stateCount ===\n" + chunk + "\n")
    idx = html.find('stateCount', idx+1)

# Find tab click
idx = html.find("data-tab).classList")
if idx != -1:
    out.append("=== tab click ===\n" + html[max(0,idx-300):idx+200] + "\n")

# Find news title
idx = html.find("news-item-title")
while idx != -1:
    chunk = html[max(0,idx-50):idx+200]
    if 'item.title' in chunk:
        out.append("=== news title ===\n" + chunk + "\n")
    idx = html.find("news-item-title", idx+1)

with open('snippets_out.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print("Written to snippets_out.txt")
