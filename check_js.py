import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Extract the main script block
m = re.search(r'<script>([\s\S]*?)</script>\s*(?=<!--|\s*$)', html)
if not m:
    # Try last script tag
    matches = list(re.finditer(r'<script>([\s\S]*?)</script>', html))
    print(f"Found {len(matches)} script blocks")
    js = matches[-1].group(1) if matches else ""
else:
    js = m.group(1)

print(f"JS length: {len(js):,} chars")

# Write JS to temp file and check with node
with open('_temp_check.js', 'w', encoding='utf-8') as f:
    # Stub out browser globals so node can parse it
    f.write("const d3={json:()=>{},select:()=>({attr:()=>({selectAll:()=>({data:()=>({enter:()=>({append:()=>({attr:()=>({on:()=>{}})})})})})})},geoAlbersUsa:()=>({fitSize:()=>{}}),geoPath:()=>({projection:()=>{}}),interpolate:()=>{},scaleSequential:()=>({domain:()=>({interpolator:()=>{}})})};const topojson={feature:()=>({features:[]}),mesh:()=>{}};const FALLBACK_DATA={cros:[],service_categories:[],biotech_hub_weights:{}};")
    f.write(js)

import subprocess
result = subprocess.run(['node', '--check', '_temp_check.js'], capture_output=True, text=True)
print("Node syntax check stdout:", result.stdout)
print("Node syntax check stderr:", result.stderr)
print("Return code:", result.returncode)

import os; os.remove('_temp_check.js')
