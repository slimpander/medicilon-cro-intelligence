import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add mapProjection and mapSvg as module-level vars near other app state vars
old_state = 'let selectedState = null;'
new_state = 'let selectedState = null;\nlet mapProjection = null;\nlet mapSvgEl = null;'
if old_state in html:
    html = html.replace(old_state, new_state, 1)
    print("OK: mapProjection/mapSvgEl globals added")
else:
    # Try minified version
    old_state2 = 'let selectedState=null;'
    new_state2 = 'let selectedState=null;\nlet mapProjection=null;\nlet mapSvgEl=null;'
    if old_state2 in html:
        html = html.replace(old_state2, new_state2, 1)
        print("OK: mapProjection/mapSvgEl globals added (minified)")
    else:
        print("WARNING: selectedState not found")

# 2. In renderMap(), after projection is created, store it globally
# Find: const projection = d3.geoAlbersUsa() or similar
idx = html.find('d3.geoAlbersUsa()')
if idx != -1:
    # Find the start of that const/let statement
    line_start = html.rfind('\n', 0, idx) + 1
    line_end = html.find(';', idx) + 1
    old_proj_line = html[line_start:line_end]
    new_proj_line = old_proj_line + '\n  mapProjection=projection;\n  mapSvgEl=svg;'
    if old_proj_line in html:
        html = html.replace(old_proj_line, new_proj_line, 1)
        print("OK: projection stored to global")
    else:
        print("WARNING: projection line replacement failed")
else:
    print("WARNING: geoAlbersUsa not found")

# 3. In openDetailPanel, add city dot render call at end
# Find the panel.classList.add('open') line
old_open = "document.getElementById('detail-panel').classList.add('open');"
new_open = old_open + "\n  if(mapSvgEl&&mapProjection)renderCityDots(mapSvgEl,mapProjection,abbr);"
if old_open in html:
    html = html.replace(old_open, new_open, 1)
    print("OK: renderCityDots wired to openDetailPanel")
else:
    # Try alternate
    old_open2 = "panel.classList.add('open');"
    idx = html.find(old_open2)
    if idx != -1:
        # Make sure we're inside openDetailPanel context
        context_start = html.rfind('function openDetailPanel', 0, idx)
        context_end = html.find('\nfunction ', idx)
        if context_start != -1 and idx < context_end:
            html = html[:idx+len(old_open2)] + "\n  if(mapSvgEl&&mapProjection)renderCityDots(mapSvgEl,mapProjection,abbr);" + html[idx+len(old_open2):]
            print("OK: renderCityDots wired (alt form)")
        else:
            print("WARNING: panel.classList.add('open') found but not in openDetailPanel")
    else:
        print("WARNING: could not find panel open call")

# 4. Clear city dots on panel close
old_close = 'function closeDetailPanel(){'
idx = html.find(old_close)
if idx != -1:
    close_end = html.find('}', idx) + 1
    old_close_fn = html[idx:close_end]
    new_close_fn = old_close_fn.rstrip('}') + "\n  if(mapSvgEl)mapSvgEl.selectAll('.city-dot').remove();\n}"
    html = html.replace(old_close_fn, new_close_fn, 1)
    print("OK: city dots cleared on panel close")
else:
    print("WARNING: closeDetailPanel not found")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Done. Size: {len(html)}")
