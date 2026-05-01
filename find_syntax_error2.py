import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find the script block start
script_start = html.find('<script>')
script_end = html.find('</script>', script_start)
script_content = html[script_start + len('<script>'):script_end]

# Split into lines and show around line 149
js_lines = script_content.split('\n')
print(f"Script block: {len(js_lines)} lines total")
print()
print("=== JS lines 144-155 ===")
for i, line in enumerate(js_lines[143:156], start=144):
    marker = " <<<<" if i == 149 else ""
    print(f"{i:4d}: {line[:120]}{marker}")

print()
# Also search for any stray ')' that might be a syntax error
print("=== Searching for suspicious lone ')' patterns ===")
for m in re.finditer(r'\)\s*\n\s*\)', script_content):
    lineno = script_content[:m.start()].count('\n') + 1
    print(f"Line ~{lineno}: {repr(script_content[m.start()-30:m.start()+30])}")
