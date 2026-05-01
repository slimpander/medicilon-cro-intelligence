import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

checks = [
    'initNewsPanel', 'setupNewsPanel', 'openNewsPanel',
    'openNewsForState', 'getStateDominantColor', 'renderLegendSwatches',
    'hexWithAlpha', 'getStateDominant',
    'openCroModal', 'estimateClients', 'renderStrategyPanel',
    'news.google.com', 'legend-swatches', 'legend-max',
    'dominant', 'SERVICE_COLORS'
]
for c in checks:
    print(('OK' if c in html else 'MISSING') + '  ' + c)
