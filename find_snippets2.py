with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find company legend block more broadly
idx = html.find('stateCount')
while idx != -1:
    chunk = html[max(0,idx-200):idx+400]
    print("=== stateCount context ===")
    print(repr(chunk))
    print()
    idx = html.find('stateCount', idx+1)
