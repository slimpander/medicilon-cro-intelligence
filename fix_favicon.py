with open('index.html','r',encoding='utf-8') as f:
    html = f.read()

favicon = '<link rel="icon" href="data:,">\n  '
if '<link rel="icon"' not in html:
    html = html.replace('<meta charset', favicon + '<meta charset', 1)
    print('Favicon added')

with open('index.html','w',encoding='utf-8') as f:
    f.write(html)
