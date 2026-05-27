/**
 * LinkedIn Monitor — Popup Script v2
 * Supports MutationObserver auto-scan + manual scan fallback
 */
const API_BASE = 'http://localhost:8000/api';
const DEFAULT_KEYWORDS = [
  'DMPK', 'ADME', 'pharmacokinetics', 'drug metabolism', 'preclinical',
  'toxicology', 'safety assessment', 'IND', 'bioanalysis', 'bioanalytical',
  'GLP', 'in vivo', 'efficacy', 'animal study', 'mouse model',
  'CRO', 'CDMO', 'contract research', 'outsourcing', 'partner',
  'collaboration', 'vendor', 'RFP', 'strategic partner',
  'drug discovery', 'lead optimization', 'clinical trial', 'Phase 1',
  'Phase 2', 'Phase 3', 'candidate', 'pipeline', 'antibody', 'mAb',
  'ADC', 'biologic', 'cell therapy', 'gene therapy', 'small molecule',
  'PROTAC', 'CMC', 'formulation', 'manufacturing',
  'Series A', 'Series B', 'Series C', 'funding', 'raised', 'financing',
  'IPO', 'venture', 'seed', 'investment', 'investor',
  'biotech', 'biopharma', 'pharma', 'therapeutic', 'oncology',
  'immunology', 'neuroscience', 'rare disease', 'FDA', 'approval',
];
const TITLE_KEYWORDS = [
  'CSO', 'Chief Scientific Officer', 'VP R&D', 'VP Research',
  'Head of Preclinical', 'Head of DMPK', 'Head of Pharmacology',
  'Director of Toxicology', 'SVP Discovery', 'CEO', 'CTO',
  'Head of Outsourcing', 'Director CMC', 'VP Chemistry',
  'Director Bioanalysis', 'Senior Director'
];

// ── State ──────────────────────────────────────────────────────────
let connectionStatus = 'checking';
let autoScanEnabled = true;
let observerStatus = { active: false, postsDetected: 0, scanCount: 0 };
let stats = { posts: 0, contacts: 0, matches: 0, totalScore: 0, scored: 0 };
let recentMatches = [];
let activityLog = [];

// ── Init ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await loadState();
  renderAll();
  setupListeners();
  checkConnection();

  // Check observer status from active LinkedIn tab
  checkObserverStatus();

  // Refresh every 10s
  setInterval(async () => {
    await loadState();
    renderStats();
    renderRecentPosts();
  }, 10000);

  // Poll observer status every 5s
  setInterval(checkObserverStatus, 5000);
});

async function loadState() {
  return new Promise(resolve => {
    chrome.storage.local.get(['stats', 'recentMatches', 'activityLog', 'autoScanEnabled'], (data) => {
      if (data.stats) stats = data.stats;
      if (data.recentMatches) recentMatches = data.recentMatches.slice(-20);
      if (data.activityLog) activityLog = data.activityLog.slice(-30);
      if (data.autoScanEnabled !== undefined) autoScanEnabled = data.autoScanEnabled;
      resolve();
    });
  });
}

async function saveState() {
  return chrome.storage.local.set({ stats, recentMatches, activityLog, autoScanEnabled });
}

function log(message) {
  const now = new Date();
  const time = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  activityLog.push({ time, message });
  if (activityLog.length > 50) activityLog.shift();
  renderActivityLog();
  saveState();
}

// ── Connection Check ───────────────────────────────────────────────
async function checkConnection() {
  try {
    const r = await fetch(`${API_BASE}/health`);
    connectionStatus = r.ok ? 'online' : 'offline';
  } catch {
    connectionStatus = 'offline';
  }
  updateConnectionBadge();
}

async function checkObserverStatus() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url || !tab.url.includes('linkedin.com')) {
      observerStatus = { active: false, postsDetected: 0, scanCount: 0 };
    } else {
      try {
        const resp = await chrome.tabs.sendMessage(tab.id, { action: 'getStatus' });
        if (resp) observerStatus = resp;
      } catch (e) {
        // Content script not loaded
        observerStatus = { active: false, postsDetected: 0, scanCount: 0 };
      }
    }
  } catch (e) {
    observerStatus = { active: false, postsDetected: 0, scanCount: 0 };
  }
  updateObserverBadge();
}

function updateConnectionBadge() {
  const el = document.getElementById('connection-status');
  if (!el) return;
  el.className = 'status';
  if (connectionStatus === 'online') {
    el.textContent = 'Connected';
    el.classList.add('online');
  } else {
    el.textContent = 'Offline';
    el.classList.add('offline');
  }
}

function updateObserverBadge() {
  const el = document.getElementById('observer-status');
  if (!el) return;
  if (observerStatus.active) {
    el.textContent = `🟢 Auto-Scan Active (${observerStatus.postsDetected} posts)`;
    el.style.color = '#27AE60';
  } else {
    el.textContent = '⚪ Auto-Scan Inactive';
    el.style.color = '#999';
  }
}

// ── Render ─────────────────────────────────────────────────────────
function renderAll() {
  renderStats();
  renderKeywords();
  renderRecentPosts();
  renderActivityLog();
}

function renderStats() {
  document.getElementById('stat-posts').textContent = stats.posts;
  document.getElementById('stat-contacts').textContent = stats.contacts;
  document.getElementById('stat-matches').textContent = stats.matches;
  document.getElementById('stat-score').textContent =
    stats.scored > 0 ? Math.round(stats.totalScore / stats.scored) : '-';
}

function renderKeywords() {
  const el = document.getElementById('keyword-tags');
  el.innerHTML = DEFAULT_KEYWORDS.slice(0, 12).map(k =>
    `<span class="keyword-tag">${k}</span>`
  ).join('') + '<span class="keyword-tag" style="background:#eee;color:#999">+ more</span>';
}

function renderRecentPosts() {
  const el = document.getElementById('recent-posts');
  if (!recentMatches.length) {
    el.innerHTML = '<div class="empty">No posts scanned yet. Visit LinkedIn feed — auto-scan will detect posts as you scroll.</div>';
    return;
  }
  el.innerHTML = recentMatches.slice(-8).reverse().map(p => {
    const score = Math.round(p.score || 0);
    const scoreColor = score >= 50 ? '#27AE60' : score >= 20 ? '#E67E22' : '#999';
    return `
      <div class="post-item">
        <span class="score" style="color:${scoreColor}">${Math.round(p.score)}%</span>
        <div class="author">${p.author || 'Unknown'}</div>
        ${p.authorTitle ? `<div style="font-size:10px;color:#2E75B6">${p.authorTitle}${p.authorCompany ? ' · ' + p.authorCompany : ''}</div>` : ''}
        <div class="text">${(p.content || '').slice(0, 120)}</div>
        <div class="meta">${p.matchedKeywords?.slice(0,3).join(', ') || ''} · ${p.time || ''}</div>
      </div>
    `;
  }).join('');
}

function renderActivityLog() {
  const el = document.getElementById('activity-log');
  el.innerHTML = activityLog.slice(-15).map(l =>
    `<div class="log-item"><span class="time">${l.time}</span> ${l.message}</div>`
  ).join('');
}

// ── Scoring ────────────────────────────────────────────────────────
function scorePost(post) {
  const content = (post.content || '').toLowerCase();
  const allText = (post.authorTitle + ' ' + content).toLowerCase();
  const matchedKeywords = DEFAULT_KEYWORDS.filter(kw =>
    allText.includes(kw.toLowerCase())
  );

  const isDecisionMaker = TITLE_KEYWORDS.some(t =>
    (post.authorTitle || '').toLowerCase().includes(t.toLowerCase())
  );

  let score = matchedKeywords.length * 12;
  if (isDecisionMaker) score += 25;
  if (post.authorCompany && content.length > 80) score += 8;
  if (content.length > 30 && /(pharma|biotech|drug|therapeutic|clinical|research|development)/i.test(content)) {
    score = Math.max(score, 10);
  }
  score = Math.min(100, score);
  return { score, matchedKeywords, isDecisionMaker };
}

async function processAndStorePost(post) {
  const { score, matchedKeywords, isDecisionMaker } = scorePost(post);

  if (score > 0 || matchedKeywords.length > 0 || isDecisionMaker) {
    stats.matches++;
    stats.totalScore += score;
    stats.scored++;

    const match = {
      post_url: post.url || '',
      author: post.author || 'Unknown',
      authorTitle: post.authorTitle || '',
      authorCompany: post.authorCompany || '',
      content: post.content || post.text || '',
      post_date: post.date || new Date().toISOString(),
      relevance_score: score,
      matched_keywords: matchedKeywords.join(', '),
      time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      score,
      matchedKeywords,
    };

    recentMatches.push(match);
    if (recentMatches.length > 100) recentMatches = recentMatches.slice(-100);
    await sendToBackend(match);
    return true;
  }
  return false;
}

async function sendToBackend(match) {
  try {
    const r = await fetch(`${API_BASE}/linkedin/posts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(match),
    });
    if (r.ok) {
      log(`  → Sent: ${(match.author || 'Unknown')} (score: ${match.score})`);
    }
  } catch (e) {
    // Backend not running — ok, extension works standalone
  }
}

// ── Event Listeners ────────────────────────────────────────────────
async function setupListeners() {
  // Manual scan button
  document.getElementById('scan-btn')?.addEventListener('click', manualScan);

  // Auto-scan toggle
  const toggle = document.getElementById('autoscan-toggle');
  if (toggle) {
    toggle.checked = autoScanEnabled;
    toggle.addEventListener('change', async (e) => {
      autoScanEnabled = e.target.checked;
      await saveState();
      toggleAutoScan(autoScanEnabled);
    });
  }

  // Listen for auto-detected posts from content script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'newPostsDetected' && autoScanEnabled) {
      handleAutoDetectedPosts(request.posts);
      sendResponse({ ok: true });
    }
    return true;
  });
}

async function toggleAutoScan(enable) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url?.includes('linkedin.com')) {
      log(enable ? 'Navigate to LinkedIn to enable auto-scan' : 'Auto-scan disabled');
      return;
    }
    const action = enable ? 'startObserver' : 'stopObserver';
    await chrome.tabs.sendMessage(tab.id, { action });
    log(enable ? '🟢 Auto-scan enabled — detecting posts as you scroll' : '⚪ Auto-scan disabled');
    checkObserverStatus();
  } catch (e) {
    log(`Auto-scan toggle failed: ${e.message}`);
  }
}

async function handleAutoDetectedPosts(posts) {
  stats.posts += posts.length;
  let matched = 0;

  for (const post of posts) {
    const wasMatch = await processAndStorePost(post);
    if (wasMatch) matched++;
  }

  if (matched > 0) {
    log(`🤖 Auto-detected ${posts.length} posts — ${matched} matches`);
  }

  await saveState();
  renderAll();
}

async function manualScan() {
  const btn = document.getElementById('scan-btn');
  btn.disabled = true;
  btn.textContent = '⏳ Scanning...';
  document.getElementById('connection-status').className = 'status scanning';
  document.getElementById('connection-status').textContent = 'Scanning';

  log('Starting manual LinkedIn feed scan...');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab.url || !tab.url.includes('linkedin.com')) {
      log('⚠ Not on LinkedIn — navigate to linkedin.com/feed first');
      btn.disabled = false;
      btn.textContent = '🔍 Scan Current Page';
      checkConnection();
      return;
    }

    let results = null;

    // Method 1: Try content script messaging
    try {
      results = await chrome.tabs.sendMessage(tab.id, { action: 'scanFeed' });
      log('  Content script responded');
    } catch (msgErr) {
      log('  Content script not loaded, injecting scanner...');
    }

    // Method 2: Inject scanner directly
    if (!results || !results.posts) {
      try {
        const injected = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: scanLinkedInFeedPage,
        });
        if (injected && injected[0] && injected[0].result) {
          results = injected[0].result;
          log('  Scanner injected successfully');
        }
      } catch (injErr) {
        log(`  Injection failed: ${injErr.message}`);
      }
    }

    if (!results || !results.posts || !results.posts.length) {
      log('⚠ No posts found. Try scrolling the feed first, then scan again.');
      btn.disabled = false;
      btn.textContent = '🔍 Scan Current Page';
      checkConnection();
      return;
    }

    stats.posts += results.posts.length;
    let matches = 0;

    for (const post of results.posts) {
      const wasMatch = await processAndStorePost(post);
      if (wasMatch) matches++;
    }

    log(`✅ Scanned ${results.posts.length} posts — ${matches} matches found`);
    if (matches > 0) {
      stats.contacts += results.contacts_found || 0;
    }
  } catch (e) {
    log(`❌ Scan failed: ${e.message}`);
    console.error('Scan error:', e);
  }

  btn.disabled = false;
  btn.textContent = '🔍 Scan Current Page';
  await saveState();
  renderAll();
  checkConnection();
}

/**
 * Self-contained fallback scanner — injected when content script isn't loaded.
 */
function scanLinkedInFeedPage() {
  const posts = [];
  const seen = new Set();

  const selectors = [
    'div.feed-shared-update-v2',
    'article.feed-shared-update-v2',
    'div[data-urn*="urn:li:activity"]',
    '.occludable-update',
    'div.update-components-actor',
  ];

  let containers = [];
  for (const sel of selectors) {
    const found = document.querySelectorAll(sel);
    if (found.length > 2) { containers = Array.from(found); break; }
  }

  if (!containers.length) {
    document.querySelectorAll('div[dir="ltr"] > span[dir="ltr"], article p').forEach(el => {
      const text = el.textContent.trim();
      if (text.length > 30 && text.length < 2000) {
        const hash = text.slice(0, 80).toLowerCase();
        if (!seen.has(hash)) {
          seen.add(hash);
          posts.push({
            author: 'LinkedIn User', authorTitle: '', authorCompany: '',
            content: text.slice(0, 500), url: window.location.href,
            date: new Date().toISOString(),
          });
        }
      }
    });
    return { posts, contacts_found: 0 };
  }

  containers = containers.slice(0, 50);
  for (const container of containers) {
    try {
      let author = '';
      const nameEl = container.querySelector('.update-components-actor__title span[aria-hidden="true"], .feed-shared-actor__name span[aria-hidden="true"], span[dir="ltr"] > span[aria-hidden="true"]');
      if (nameEl) author = nameEl.textContent.trim();

      let authorTitle = '', authorCompany = '';
      const descEl = container.querySelector('.update-components-actor__description, .feed-shared-actor__description');
      if (descEl) {
        const text = descEl.textContent.trim();
        authorTitle = text;
        if (text.includes(' at ')) {
          const parts = text.split(' at ');
          authorTitle = parts[0].trim();
          authorCompany = parts.slice(1).join(' at ').trim();
        }
      }

      let content = '';
      const contentEl = container.querySelector('.feed-shared-update-v2__description, .feed-shared-text, .feed-shared-inline-show-more-text, .update-components-text');
      if (contentEl) content = contentEl.textContent.trim();
      if (!content && author) {
        const textEl = container.querySelector('[dir="ltr"]');
        if (textEl) { const t = textEl.textContent.trim(); content = t.startsWith(author) ? t.slice(author.length).trim() : t.slice(0, 500); }
      }

      if (!author && !content) continue;
      const hash = (author + content.slice(0, 50)).toLowerCase();
      if (!seen.has(hash)) {
        seen.add(hash);
        posts.push({
          author: author || 'LinkedIn User', authorTitle, authorCompany,
          content: content.slice(0, 800), url: '', date: '',
        });
      }
    } catch (e) {}
  }

  const contacts = new Set();
  for (const p of posts) {
    if (p.authorCompany && p.authorTitle &&
        /(CSO|VP|Head|Director|SVP|EVP|Chief|President)/i.test(p.authorTitle)) {
      contacts.add(p.authorCompany);
    }
  }

  return { posts, contacts_found: contacts.size };
}
