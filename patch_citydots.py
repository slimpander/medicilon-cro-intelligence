import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find where openDetailPanel is called from state click
# and add renderCityDots call after it
# The state click handler calls openDetailPanel(abbr)
# We need to find the projection variable to pass to renderCityDots

# Find the renderMap function and get the projection var name
idx = html.find('function openDetailPanel(')
if idx != -1:
    print("openDetailPanel:", html[idx:idx+60])

# Find the state click handler
idx2 = html.find(".on('click'")
count = 0
while idx2 != -1 and count < 10:
    chunk = html[idx2:idx2+200]
    if 'openDetailPanel' in chunk or 'abbr' in chunk:
        print(f"click handler at {idx2}:", chunk[:150])
        print("---")
    idx2 = html.find(".on('click'", idx2+1)
    count += 1
