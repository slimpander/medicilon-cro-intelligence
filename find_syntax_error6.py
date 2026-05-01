import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    all_lines = f.readlines()

# Show lines 1200-1220 (around the reported error)
print("=== HTML lines 1200-1220 ===")
for i in range(1199, 1220):
    print(f"{i+1:4d}: {all_lines[i]}", end='')

# Also extract just the script and check with node acorn-style
# Write script lines only to a JS file
script_start = None
script_end = None
for i, line in enumerate(all_lines):
    if '<script>' in line and 'src=' not in line:
        script_start = i
    if script_start and '</script>' in line and i > script_start:
        script_end = i
        break

print(f"\n\nScript: lines {script_start+1} to {script_end+1}")
js_lines = all_lines[script_start+1:script_end]
with open('_check.js', 'w', encoding='utf-8') as f:
    f.writelines(js_lines)

import subprocess
r = subprocess.run(['node', '--check', '_check.js'], capture_output=True, text=True)
print("\nNode check:")
print(r.stderr[:1000] if r.stderr else "No errors!")
print("Return code:", r.returncode)

import os; os.remove('_check.js')
