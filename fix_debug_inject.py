with open('index.html','r',encoding='utf-8') as f:
    html = f.read()

# Inject error catcher + tab debug logger right after <script> opens
DEBUG_JS = """
// ── DEBUG: catch all errors visibly ──────────────────────────────────────────
window.onerror = function(msg, src, line, col, err) {
  const b = document.getElementById('error-banner') || document.body;
  b.style.display = 'block';
  b.textContent = 'JS ERROR line ' + line + ': ' + msg;
  b.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#e74c3c;color:#fff;padding:8px 12px;z-index:9999;font-size:12px;';
  console.error('GLOBAL ERROR:', msg, 'line:', line, err);
  return false;
};
window.addEventListener('unhandledrejection', e => {
  console.error('UNHANDLED PROMISE:', e.reason);
  const b = document.getElementById('error-banner') || document.body;
  if (b) { b.style.display='block'; b.textContent='Promise error: '+e.reason; }
});
"""

SCRIPT_START = html.find('<script>') + len('<script>')
# Insert after the script tag and before FALLBACK_DATA
insert_at = html.find('const FALLBACK_DATA', SCRIPT_START)
if insert_at > 0:
    html = html[:insert_at] + DEBUG_JS + '\n' + html[insert_at:]
    print('Debug error catcher injected')

with open('index.html','w',encoding='utf-8') as f:
    f.write(html)
