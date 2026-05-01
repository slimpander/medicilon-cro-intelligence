import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Wire city dots: when state is clicked, call renderCityDots
# Also need to find where projection is accessible

# Check if projection is a module-level var or local
idx = html.find('const projection=')
idx2 = html.find('let projection')
idx3 = html.find('var projection')
print(f"projection const: {idx}, let: {idx2}, var: {idx3}")

# Check openDetailPanel for where we can inject city dot rendering
idx4 = html.find('function openDetailPanel(abbr){')
if idx4 != -1:
    chunk = html[idx4:idx4+400]
    print("openDetailPanel body:", chunk)
