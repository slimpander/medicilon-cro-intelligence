import sys, re, subprocess
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    all_lines = f.readlines()

total = len(all_lines)
print(f"Total HTML lines: {total}")

# Browser said line 149 -- show lines around it
# But also check if it means line 149 of the script block
# Find where <script> starts (line number)
script_line = None
for i, line in enumerate(all_lines, 1):
    if '<script>' in line and 'src=' not in line:
        script_line = i
        print(f"<script> tag at HTML line {i}")

# Browser line 149 could mean:
# Option A: HTML line 149
print("\n=== HTML lines 147-152 ===")
for i in range(146, 153):
    print(f"{i+1:4d}: {all_lines[i][:120]}", end='')

# Option B: script_line + 149
if script_line:
    offset_line = script_line + 149 - 1
    print(f"\n\n=== HTML lines around script+149 (line {offset_line}) ===")
    for i in range(max(0, offset_line-3), min(total, offset_line+3)):
        marker = " <<<" if i+1 == offset_line else ""
        print(f"{i+1:4d}: {all_lines[i][:120]}{marker}", end='')

# Option C: Search for ')' that could be unexpected
# Look for unmatched parens in the news-related code we added
print("\n\n=== Searching loadNewsData / NEWS_META area ===")
for i, line in enumerate(all_lines, 1):
    if any(k in line for k in ['loadNewsData', 'NEWS_META', 'NEWS_DATA', 'setupNewsPanel']):
        print(f"{i:4d}: {line[:120]}", end='')
