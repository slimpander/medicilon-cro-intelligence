import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find and nuke the dangling catch block left behind
old = """usGeo=await d3.json('data/states-10m.json');catch(cdnErr){
      console.warn('CDN failed, trying unpkg fallback:', cdnErr.message);
      usGeo=await d3.json('data/states-10m.json');
    }"""

new = "usGeo=await d3.json('data/states-10m.json');"

if old in html:
    html = html.replace(old, new, 1)
    print("Fixed: removed dangling catch block")
else:
    # Show what's actually there
    idx = html.find("usGeo=await d3.json")
    print("Current atlas fetch block:")
    print(repr(html[idx:idx+300]))

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# Verify final init block
idx = html.find('async function init(){')
print("\nFinal init() body:")
print(html[idx:idx+500])
