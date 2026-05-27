/**
 * LinkedIn Monitor — Background Service Worker v2
 * Relays messages between content-script (auto-scan) and popup.
 * Periodic health pings and stats reporting.
 */

const POLL_INTERVAL_MINUTES = 30;

// ── Alarm Setup ────────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(() => {
  console.log('[Medicilon LinkedIn Monitor v2] Installed');
  chrome.alarms.create('linkedin-monitor', {
    periodInMinutes: POLL_INTERVAL_MINUTES,
  });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'linkedin-monitor') {
    console.log('[LinkedIn Monitor] Periodic check triggered');
    pingBackend();
  }
});

// ── Message Handling ───────────────────────────────────────────────
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // Auto-detected posts from content script → forward to popup if open
  if (request.action === 'newPostsDetected') {
    // Forward to all extension views (popup)
    chrome.runtime.sendMessage(request).catch(() => {});
    sendResponse({ ok: true });
    return true;
  }

  if (request.action === 'getStats') {
    chrome.storage.local.get(['stats'], (data) => {
      sendResponse(data.stats || { posts: 0, contacts: 0, matches: 0, totalScore: 0, scored: 0 });
    });
    return true;
  }

  if (request.action === 'clearData') {
    chrome.storage.local.set({
      stats: { posts: 0, contacts: 0, matches: 0, totalScore: 0, scored: 0 },
      recentMatches: [],
      activityLog: [],
    });
    sendResponse({ ok: true });
    return true;
  }

  if (request.action === 'sendToBackend') {
    sendToBackend(request.data).then(sendResponse);
    return true;
  }
});

// ── Backend Communication ──────────────────────────────────────────
async function pingBackend() {
  try {
    const r = await fetch('http://localhost:8000/api/health');
    if (r.ok) {
      const data = await r.json();
      console.log('[LinkedIn Monitor] Backend healthy:', data.version);
    }
  } catch (e) {
    console.log('[LinkedIn Monitor] Backend unavailable');
  }
}

async function sendToBackend(data) {
  try {
    const r = await fetch('http://localhost:8000/api/linkedin/posts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return { ok: r.ok, status: r.status };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// ── Periodic Stats Report ──────────────────────────────────────────
function reportStats() {
  chrome.storage.local.get(['stats'], (data) => {
    const s = data.stats || {};
    console.log(
      `[LinkedIn Monitor] Stats: ${s.posts || 0} posts, ${s.matches || 0} matches, ` +
      `${s.contacts || 0} contacts, avg score: ${s.scored ? Math.round(s.totalScore / s.scored) : '-'}`
    );
  });
}

setInterval(reportStats, 60000 * 30);
