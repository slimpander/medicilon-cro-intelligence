import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Check for syntax issues - look for common JS errors
# 1. Unclosed strings
# 2. getDominantService definition
idx = html.find('function getDominantService')
if idx != -1:
    print("getDominantService:", html[idx:idx+200])
else:
    # Try arrow fn
    idx2 = html.find('getDominantService')
    print("getDominantService ref:", html[max(0,idx2-30):idx2+200] if idx2!=-1 else "NOT FOUND")

# Check colorMode definition
idx3 = html.find('colorMode')
if idx3 != -1:
    print("colorMode:", html[idx3:idx3+100])

# Check init() call 
idx4 = html.find('window.addEventListener')
if idx4 != -1:
    print("window listener:", html[idx4:idx4+100])

# Check if init() is called
idx5 = html.rfind('init()')
if idx5 != -1:
    print("init() call:", html[max(0,idx5-50):idx5+50])
    
# Check for broken HTML structure - find </script> count
print("\nscript tag counts:")
print("  <script:", html.count('<script'))
print("  </script>:", html.count('</script>'))

# Check news panel hidden class  
print("\nnews-panel hidden:", 'hidden' in html[html.find('id="news-panel"'):html.find('id="news-panel"')+100] if 'id="news-panel"' in html else 'panel not found')

# Find the news-close-btn 
print("news-close-btn:", 'news-close-btn' in html)
print("news-minimize-btn:", 'news-minimize-btn' in html)
print("news-close id:", 'id="news-close"' in html)
print("news-minimize id:", 'id="news-minimize"' in html)
