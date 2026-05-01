with open('index.html', encoding='utf-8') as f:
    html = f.read()
checks = ['SERVICE_COLORS', 'news-panel', 'NEWS_DATA', 'initNewsPanel',
          'openNewsForCompany', 'openNewsForState', 'View News',
          'getStateDominantColor', 'renderLegendSwatches']
for c in checks:
    status = 'OK' if c in html else 'MISSING'
    print(status, c)
print('Size:', len(html), 'bytes')
