with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find company legend item building
idx = html.find('company-item')
while idx != -1:
    chunk = html[max(0,idx-20):idx+300]
    if 'createElement' in chunk or 'stateCount' in chunk:
        print("=== LEGEND ITEM ===")
        print(repr(chunk))
        print()
    idx = html.find('company-item', idx+1)

# Find tab click handler
idx = html.find('tab-btn')
while idx != -1:
    chunk = html[max(0,idx-10):idx+200]
    if 'addEventListener' in chunk:
        print("=== TAB BTN ===")
        print(repr(chunk))
        print()
        break
    idx = html.find('tab-btn', idx+1)

# Find news title line in renderNewsList
idx = html.find('news-item-title')
while idx != -1:
    chunk = html[max(0,idx-30):idx+120]
    if 'item.title' in chunk:
        print("=== NEWS TITLE ===")
        print(repr(chunk))
        print()
    idx = html.find('news-item-title', idx+1)
