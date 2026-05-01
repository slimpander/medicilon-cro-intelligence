import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('index.html', 'r', encoding='utf-8') as f:
    all_lines = f.readlines()

# Script starts at line 1062 (0-indexed: 1061), error at script line 429
# HTML line = 1062 + 429 - 1 = 1490
error_html_line = 1062 + 429 - 1
print(f"Error around HTML line {error_html_line}")
print("Context:")
for i in range(error_html_line - 5, error_html_line + 5):
    marker = " <<<" if i+1 == error_html_line else ""
    print(f"{i+1:4d}: {all_lines[i]}{marker}", end='')
