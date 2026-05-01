import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
# Find where selectedState is defined
idx = html.find('selectedState')
print("First occurrence:", html[max(0,idx-50):idx+80])
idx2 = html.find('selectedState', idx+1)
print("Second:", html[max(0,idx2-50):idx2+80])

# Add globals near the top of the script section, after FALLBACK_DATA
idx3 = html.find('let croData=null;')
if idx3 == -1:
    idx3 = html.find('let croData = null;')
print("croData:", html[idx3:idx3+100] if idx3 != -1 else "NOT FOUND")
