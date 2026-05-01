with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find and fix ALL remaining bare legend-max textContent assignments
import re
count_before = html.count("getElementById('legend-max').textContent")
print(f"Remaining bare legend-max refs: {count_before}")

# Safe guard all of them
html = re.sub(
    r"document\.getElementById\('legend-max'\)\.textContent\s*=\s*(\w+);",
    r"(function(){var _lm=document.getElementById('legend-max');if(_lm)_lm.textContent=\1;})();",
    html
)

count_after = html.count("getElementById('legend-max').textContent")
print(f"After fix: {count_after} remaining")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Done. Size: {len(html)} bytes")
