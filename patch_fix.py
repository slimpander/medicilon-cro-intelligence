"""Fix null reference errors after legend HTML change."""
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

fixes = 0

# Fix 1: legend-max null ref in renderMap()
old1 = "  document.getElementById('legend-max').textContent = maxCros;\n\n  // Draw states"
new1 = "  const legendMax = document.getElementById('legend-max');\n  if (legendMax) legendMax.textContent = maxCros;\n\n  // Draw states"
if old1 in html:
    html = html.replace(old1, new1, 1)
    fixes += 1
    print("Fixed: legend-max null ref in renderMap()")

# Fix 2: legend-max null ref in updateMapColors()
old2 = "  document.getElementById('legend-max').textContent = maxCros;\n\n  const colorScale"
new2 = "  const legendMax2 = document.getElementById('legend-max');\n  if (legendMax2) legendMax2.textContent = maxCros;\n\n  const colorScale"
if old2 in html:
    html = html.replace(old2, new2, 1)
    fixes += 1
    print("Fixed: legend-max null ref in updateMapColors()")

# Also guard any remaining bare getElementById('legend-max')
remaining = html.count("getElementById('legend-max').textContent")
if remaining > 0:
    print(f"WARNING: {remaining} remaining unguarded legend-max references")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done. {fixes} fixes applied. Size: {len(html)} bytes")
