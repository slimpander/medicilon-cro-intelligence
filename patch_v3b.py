"""patch_v3b.py — Fix the 3 missed injections from patch_v3.py"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

print(f"Starting size: {len(html)}")
fixes = 0

# ── 1. Company legend: add click handler ────────────────────────────────────
# The minified version from original renderSidebar
OLD_LEGEND = "const legend=document.getElementById('company-legend');legend.innerHTML='';\n  croData.cros.forEach(cro=>{\n    const div=document.createElement('div');\n    div.className='company-item'+(cro.is_medicilon?' medicilon':'');\n    const stateCount=cro.is_medicilon?'\u2014':(cro.states?.length||0);\n    div.innerHTML=`\n      <div class=\"company-dot\" style=\"background:${croColors[cro.id]}\"></div>\n      <div class=\"company-name\">${cro.short_name}</div>\n      <div class=\"company-states\">${stateCount} states</div>\n    `;\n    legend.appendChild(div);"

# Search for the actual text
idx = html.find("legend.appendChild(div);")
if idx != -1:
    # Find the enclosing legend block
    start = html.rfind("const legend=document.getElementById('company-legend')", 0, idx)
    if start != -1:
        block = html[start:idx+25]
        print("Found legend block, length:", len(block))
        # Build replacement
        new_block = block.rstrip()
        # Add click handler just before legend.appendChild(div)
        new_block = new_block.replace(
            "legend.appendChild(div);",
            "div.style.cursor='pointer';\n    div.title='Click for company profile';\n    div.addEventListener('click',()=>openCroModal(cro.id));\n    legend.appendChild(div);"
        )
        html = html[:start] + new_block + html[start+len(block):]
        fixes += 1
        print("OK: Company legend click handler added")
    else:
        print("WARNING: legend block start not found")
else:
    print("WARNING: legend.appendChild(div) not found")

# ── 2. Tab click: add strategy render ───────────────────────────────────────
OLD_TAB = "btn.classList.add('active');const pane=document.getElementById('tab-'+btn.dataset.tab);if(pane)pane.classList.add('active');"
NEW_TAB = "btn.classList.add('active');const pane=document.getElementById('tab-'+btn.dataset.tab);if(pane)pane.classList.add('active');if(btn.dataset.tab==='strategy')renderStrategyPanel();"

if OLD_TAB in html:
    html = html.replace(OLD_TAB, NEW_TAB, 1)
    fixes += 1
    print("OK: Strategy tab render hook added")
else:
    print("WARNING: tab click handler not found")

# ── 3. News title hyperlink ──────────────────────────────────────────────────
OLD_NEWS = """div.innerHTML='<div class="news-item-title">'+item.title+'</div><div class="news-item-meta">'+item.source+' &middot; '+item.date+'</div>"""
NEW_NEWS = """div.innerHTML='<div class="news-item-title"><a href="https://news.google.com/search?q="+encodeURIComponent(item.title)+" target=\\"_blank\\" style=\\"color:inherit;text-decoration:none\\">'+(item.title)+' <span style=\\"font-size:9px;opacity:0.5\\">&#8599;</span></a></div><div class="news-item-meta">'+item.source+' &middot; '+item.date+'</div>"""

# Try a simpler approach — just find and replace the inner title part
OLD_NEWS_SIMPLE = "+'<div class=\"news-item-title\">'+item.title+'</div>'"
NEW_NEWS_SIMPLE = "+'<div class=\"news-item-title\"><a href=\"https://news.google.com/search?q=\"+encodeURIComponent(item.title)+\"\" target=\"_blank\" style=\"color:inherit;text-decoration:none\">'+item.title+' <span style=\"font-size:9px;opacity:0.5\">&#8599;</span></a></div>'"

# Use a direct string search for what we saw in the file
target = 'div.innerHTML=\'<div class="news-item-title">\'+item.title+\'</div>'
replacement = 'div.innerHTML=\'<div class="news-item-title"><a href="https://news.google.com/search?q=\'+encodeURIComponent(item.title)+\'" target="_blank" style="color:inherit;text-decoration:none">\'+item.title+\' <span style="font-size:9px;opacity:0.5">&#8599;</span></a></div>'

if target in html:
    html = html.replace(target, replacement, 1)
    fixes += 1
    print("OK: News title hyperlinks added")
else:
    # Try alternate form without semicolons
    target2 = "div.innerHTML='<div class=\"news-item-title\">'+item.title+'</div>"
    if target2 in html:
        repl2 = "div.innerHTML='<div class=\"news-item-title\"><a href=\"https://news.google.com/search?q=\"+encodeURIComponent(item.title)+\"\" target=\"_blank\" style=\"color:inherit;text-decoration:none\">'+item.title+' <span style=\"font-size:9px;opacity:0.5\">&#8599;</span></a></div>"
        html = html.replace(target2, repl2, 1)
        fixes += 1
        print("OK: News title hyperlinks added (alt form)")
    else:
        print("WARNING: news title injection point not found")

# ── Write ────────────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done. {fixes}/3 fixes. Final size: {len(html)}")
checks = ['openCroModal(cro.id)', 'renderStrategyPanel()', 'news.google.com']
for c in checks:
    print(('OK' if c in html else 'MISSING') + '  ' + c)
