import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find getStateColor definition
idx = html.find('function getStateColor')
if idx != -1:
    print("getStateColor:", html[idx:idx+400])
else:
    print("getStateColor not found as function")
    # Maybe it's a const or arrow fn
    idx2 = html.find('getStateColor')
    while idx2 != -1:
        print("ref:", html[max(0,idx2-20):idx2+150])
        print("---")
        idx2 = html.find('getStateColor', idx2+1)

# Find filterNewsByState
idx3 = html.find('filterNewsByState')
if idx3 != -1:
    print("filterNewsByState:", html[idx3:idx3+200])
else:
    print("filterNewsByState: NOT FOUND")

# Find filterNewsByCompany
idx4 = html.find('filterNewsByCompany')
if idx4 != -1:
    print("filterNewsByCompany:", html[idx4:idx4+200])
