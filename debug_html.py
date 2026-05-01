with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Check for leftover colorScale references
import re
lines = html.split('\n')
for i, line in enumerate(lines, 1):
    if 'colorScale' in line:
        print(f"Line {i}: {line.strip()}")

# Check for duplicate function definitions
fns = ['renderLegendSwatches', 'getStateDominantColor', 'hexWithAlpha', 'initNewsPanel', 'renderNewsList']
for fn in fns:
    count = html.count('function ' + fn)
    print(f"function {fn}: {count} definition(s)")

# Check for syntax issues — unclosed backtick template literals in key areas
bt_count = html.count('`')
print(f"\nBacktick count: {bt_count} ({'even - OK' if bt_count % 2 == 0 else 'ODD - POSSIBLE ISSUE'})")

# Check the colorScale definition still exists
print(f"\ncolorScale defined: {'scaleSequential' in html}")
print(f"colorScale referenced (fill): {html.count('colorScale(')}")
