import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Show the full init() function body
idx = html.find('async function init(){')
# Find its closing brace by counting depth
depth = 0
i = idx
in_func = False
for j in range(idx, min(idx + 5000, len(html))):
    if html[j] == '{':
        depth += 1
        in_func = True
    elif html[j] == '}':
        depth -= 1
        if in_func and depth == 0:
            end = j + 1
            break

print(html[idx:end])
