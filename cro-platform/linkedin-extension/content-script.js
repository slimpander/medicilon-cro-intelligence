/**
 * LinkedIn Feed Scanner v2 — MutationObserver-based auto-detection
 * Detects new posts dynamically as user scrolls, no manual "Scan" button needed.
 * Keeps legacy scanLinkedInFeed() for manual fallback and Chrome messaging.
 */
(function () {
  'use strict';

  const POST_SELECTORS = [
    'div.feed-shared-update-v2',
    'article.feed-shared-update-v2',
    'div[data-urn*="urn:li:activity"]',
    'div[data-urn*="urn:li:share"]',
    '.occludable-update',
    'div.update-components-actor',
  ];

  const processedPosts = new Set();
  let observerActive = false;
  let scanCount = 0;

  // ── Post Extraction ──────────────────────────────────────────────

  function extractPost(container) {
    try {
      let author = '';
      let authorTitle = '';
      let authorCompany = '';

      // Author name
      const namePatterns = [
        '.update-components-actor__title span[aria-hidden="true"]',
        '.feed-shared-actor__name span[aria-hidden="true"]',
        '.update-components-actor__name',
        'span[dir="ltr"] > span[aria-hidden="true"]',
        '.feed-shared-actor__name span',
        'strong span[aria-hidden="true"]',
        '[class*="actor__name"] span[aria-hidden="true"]',
      ];
      for (const pat of namePatterns) {
        const el = container.querySelector(pat);
        if (el && el.textContent.trim().length > 1) {
          author = el.textContent.trim();
          break;
        }
      }

      // Author subtitle
      const subtitlePatterns = [
        '.update-components-actor__description',
        '.feed-shared-actor__description',
        '.update-components-actor__subtitle',
        '[class*="actor__subtitle"]',
      ];
      for (const pat of subtitlePatterns) {
        const el = container.querySelector(pat);
        if (el && el.textContent.trim()) {
          const text = el.textContent.trim();
          authorTitle = text;
          if (text.includes(' at ')) {
            const parts = text.split(' at ');
            authorTitle = parts[0].trim();
            authorCompany = parts.slice(1).join(' at ').trim();
          }
          break;
        }
      }

      // Content
      let content = '';
      const contentPatterns = [
        '.feed-shared-update-v2__description',
        '.feed-shared-text',
        '.feed-shared-inline-show-more-text',
        '.update-components-text',
        '[class*="update__description"]',
        '[class*="feed-shared__text"]',
      ];
      for (const pat of contentPatterns) {
        const el = container.querySelector(pat);
        if (el && el.textContent.trim().length > 10) {
          content = el.textContent.trim();
          break;
        }
      }

      // Date
      let dateStr = '';
      const dateEl = container.querySelector('time[datetime]');
      if (dateEl) {
        dateStr = dateEl.getAttribute('datetime') || dateEl.textContent.trim();
      }

      // Post URL
      let postUrl = '';
      const linkPatterns = [
        'a[href*="/feed/update/"]',
        'a[href*="/posts/"]',
      ];
      for (const pat of linkPatterns) {
        const el = container.querySelector(pat);
        if (el && el.href) {
          postUrl = el.href;
          break;
        }
      }

      if (!author && !content) return null;

      // Unique hash for dedup
      const hash = (author + content.slice(0, 80)).toLowerCase().replace(/\s+/g, '');
      if (processedPosts.has(hash)) return null;

      return {
        hash,
        author: author || 'LinkedIn User',
        authorTitle,
        authorCompany,
        content: content.slice(0, 800),
        url: postUrl,
        date: dateStr,
      };
    } catch (e) {
      return null;
    }
  }

  // ── Post Processing & Reporting ──────────────────────────────────

  function processNewPosts(newPosts) {
    if (!newPosts.length) return;

    for (const post of newPosts) {
      processedPosts.add(post.hash);
    }

    scanCount += newPosts.length;

    // Send to background/popup for scoring
    try {
      chrome.runtime.sendMessage({
        action: 'newPostsDetected',
        posts: newPosts.map(p => ({
          author: p.author,
          authorTitle: p.authorTitle,
          authorCompany: p.authorCompany,
          content: p.content,
          url: p.url,
          date: p.date,
        })),
        count: newPosts.length,
      }).catch(() => {
        // Background may not be listening — that's fine
      });
    } catch (e) {
      // Ignore messaging errors
    }

    console.log(
      `%c[Medicilon Auto-Scan] %c+${newPosts.length} new posts %c(total: ${processedPosts.size})`,
      'color:#2E75B6;font-weight:bold',
      'color:#27AE60;font-weight:bold',
      'color:#999'
    );
  }

  // ── Scan DOM for New Posts ───────────────────────────────────────

  function scanForNewPosts() {
    let containers = [];

    for (const sel of POST_SELECTORS) {
      const found = document.querySelectorAll(sel);
      if (found.length > 2) {
        containers = Array.from(found);
        break;
      }
    }

    if (!containers.length) return;

    const newPosts = [];
    for (const container of containers.slice(0, 100)) {
      const post = extractPost(container);
      if (post) newPosts.push(post);
    }

    processNewPosts(newPosts);
  }

  // ── MutationObserver Setup ───────────────────────────────────────

  function startObserver() {
    if (observerActive) return;
    observerActive = true;

    // Initial scan
    scanForNewPosts();

    // Watch for DOM changes (new posts loaded via infinite scroll)
    const observer = new MutationObserver((mutations) => {
      let hasNewNodes = false;

      for (const mutation of mutations) {
        if (mutation.addedNodes.length > 0) {
          for (const node of mutation.addedNodes) {
            if (node.nodeType === Node.ELEMENT_NODE) {
              // Check if the added node or its children contain feed posts
              for (const sel of POST_SELECTORS) {
                if (node.matches?.(sel) || node.querySelector?.(sel)) {
                  hasNewNodes = true;
                  break;
                }
              }
              if (hasNewNodes) break;
            }
          }
        }
        if (hasNewNodes) break;
      }

      if (hasNewNodes) {
        // Debounce: wait 500ms after last mutation before scanning
        clearTimeout(observer._debounceTimer);
        observer._debounceTimer = setTimeout(() => {
          scanForNewPosts();
        }, 500);
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    console.log('%c[Medicilon Auto-Scan] %cObserver active — detecting new posts as you scroll',
      'color:#2E75B6;font-weight:bold', 'color:#666');
  }

  function stopObserver() {
    observerActive = false;
    console.log('%c[Medicilon Auto-Scan] %cObserver stopped',
      'color:#2E75B6;font-weight:bold', 'color:#999');
  }

  // ── Legacy: Manual Scan (kept for Chrome messaging) ──────────────

  function scanLinkedInFeed() {
    const posts = [];
    const seen = new Set();

    let containers = [];
    for (const sel of POST_SELECTORS) {
      const found = document.querySelectorAll(sel);
      if (found.length > 2) {
        containers = Array.from(found);
        break;
      }
    }

    if (!containers.length) {
      // Generic fallback
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
    for (const c of containers) {
      const post = extractPost(c);
      if (post) {
        posts.push({
          author: post.author,
          authorTitle: post.authorTitle,
          authorCompany: post.authorCompany,
          content: post.content,
          url: post.url,
          date: post.date,
        });
      }
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

  // ── Chrome Message Handlers ──────────────────────────────────────

  if (typeof chrome !== 'undefined' && chrome.runtime?.onMessage) {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action === 'scanFeed') {
        try {
          const result = scanLinkedInFeed();
          sendResponse(result);
        } catch (e) {
          sendResponse({ posts: [], contacts_found: 0, error: e.message });
        }
        return true;
      }

      if (request.action === 'startObserver') {
        startObserver();
        sendResponse({ ok: true, active: observerActive });
        return true;
      }

      if (request.action === 'stopObserver') {
        stopObserver();
        sendResponse({ ok: true, active: observerActive });
        return true;
      }

      if (request.action === 'getStatus') {
        sendResponse({
          active: observerActive,
          postsDetected: processedPosts.size,
          scanCount,
        });
        return true;
      }
    });
  }

  // ── Auto-start ───────────────────────────────────────────────────

  // Auto-start observer when content script loads on LinkedIn feed
  if (window.location.hostname.includes('linkedin.com')) {
    // Wait for feed to render before starting
    setTimeout(startObserver, 2000);
  }
})();
