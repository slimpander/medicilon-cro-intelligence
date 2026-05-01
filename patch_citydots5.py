import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add mapProjection and mapSvgEl to the existing state vars line
old_state = "selectedState=null,colorMode='density';"
new_state = "selectedState=null,colorMode='density',mapProjection=null,mapSvgEl=null;"
if old_state in html:
    html = html.replace(old_state, new_state, 1)
    print("OK: globals added to state vars")
else:
    print("WARNING:", old_state, "not found")
    # Try to find and show context
    idx = html.find('selectedState=null')
    print("Context:", html[max(0,idx-30):idx+80])

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Done:", len(html))
