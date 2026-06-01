'use strict';

const FEED_URL = 'data/feed.json';

const CATEGORY_LABELS = {
  tech_global: 'Tech Global',
  tech_japan: 'Tech Japan（日本）',
  jobs_japan: '就活 / 転職',
};

// ── localStorage helpers ──────────────────────────────────────────────────────

function getReadItems() {
  try {
    return new Set(JSON.parse(localStorage.getItem('readItems') || '[]'));
  } catch {
    return new Set();
  }
}

function saveReadItems(set) {
  localStorage.setItem('readItems', JSON.stringify([...set]));
}

function getToggles() {
  try {
    const saved = JSON.parse(localStorage.getItem('categoryToggles') || '{}');
    return {
      tech_global: saved.tech_global !== false,
      tech_japan:  saved.tech_japan  !== false,
      jobs_japan:  saved.jobs_japan  !== false,
    };
  } catch {
    return { tech_global: true, tech_japan: true, jobs_japan: true };
  }
}

function saveToggles(toggles) {
  localStorage.setItem('categoryToggles', JSON.stringify(toggles));
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatAge(isoStr) {
  if (!isoStr) return '';
  const ms = Date.now() - new Date(isoStr).getTime();
  if (isNaN(ms)) return '';
  const mins  = Math.round(ms / 60_000);
  const hours = Math.round(ms / 3_600_000);
  const days  = Math.round(ms / 86_400_000);
  if (mins  <  60) return `${mins}m ago`;
  if (hours <  24) return `${hours}h ago`;
  if (days  <  30) return `${days}d ago`;
  return new Date(isoStr).toLocaleDateString();
}

// ── Rendering ─────────────────────────────────────────────────────────────────

function buildCard(item, readItems) {
  const isRead = readItems.has(item.id);
  const article = document.createElement('article');
  article.className = 'item-card' + (isRead ? ' read' : '');
  article.dataset.id = item.id;

  article.innerHTML = `
    <div class="item-meta">
      <span class="item-source">${esc(item.source)}</span>
      <span class="item-age">${formatAge(item.published)}</span>
    </div>
    <h3 class="item-title">
      <a href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a>
    </h3>
    ${item.summary ? `<p class="item-summary">${esc(item.summary)}</p>` : ''}
    <button class="mark-read-btn" data-id="${esc(item.id)}">
      ${isRead ? '✓ Read' : 'Mark read'}
    </button>
  `;

  article.querySelector('.mark-read-btn').addEventListener('click', e => {
    e.stopPropagation();
    const btn = e.currentTarget;
    const id = btn.dataset.id;
    const ids = getReadItems();
    if (ids.has(id)) {
      ids.delete(id);
    } else {
      ids.add(id);
    }
    saveReadItems(ids);
    const nowRead = ids.has(id);
    article.classList.toggle('read', nowRead);
    btn.textContent = nowRead ? '✓ Read' : 'Mark read';
  });

  return article;
}

function renderFeed(categories, readItems, toggles) {
  const container = document.getElementById('feed-container');
  container.innerHTML = '';

  for (const [catKey, label] of Object.entries(CATEGORY_LABELS)) {
    const items = categories[catKey] || [];

    const section = document.createElement('section');
    section.className = 'cat-section';
    section.dataset.cat = catKey;
    section.hidden = !toggles[catKey];

    const heading = document.createElement('h2');
    heading.className = 'cat-heading';
    heading.textContent = label;
    section.appendChild(heading);

    if (items.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'empty-msg';
      empty.textContent = 'No items yet — feed refreshes every 3 hours.';
      section.appendChild(empty);
    } else {
      for (const item of items) {
        section.appendChild(buildCard(item, readItems));
      }
    }

    container.appendChild(section);
  }
}

// ── Category toggles ──────────────────────────────────────────────────────────

function initToggles(toggles) {
  document.querySelectorAll('.cat-toggle').forEach(btn => {
    const cat = btn.dataset.cat;
    btn.classList.toggle('active', toggles[cat]);

    btn.addEventListener('click', () => {
      toggles[cat] = !toggles[cat];
      btn.classList.toggle('active', toggles[cat]);
      const section = document.querySelector(`.cat-section[data-cat="${cat}"]`);
      if (section) section.hidden = !toggles[cat];
      saveToggles(toggles);
    });
  });
}

// ── Install banner ────────────────────────────────────────────────────────────

function maybeShowInstallBanner() {
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches
    || window.navigator.standalone === true;
  if (isStandalone) return;
  if (localStorage.getItem('installBannerDismissed')) return;

  const banner = document.getElementById('install-banner');
  banner.hidden = false;
  document.getElementById('dismiss-banner').addEventListener('click', () => {
    banner.hidden = true;
    localStorage.setItem('installBannerDismissed', '1');
  });
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
  const toggles   = getToggles();
  const readItems = getReadItems();

  initToggles(toggles);
  maybeShowInstallBanner();

  try {
    const resp = await fetch(FEED_URL, { cache: 'no-cache' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    const lastUpdatedEl = document.getElementById('last-updated');
    if (data.generated_at) {
      lastUpdatedEl.textContent = `Updated ${formatAge(data.generated_at)}`;
    }

    renderFeed(data.categories || {}, readItems, toggles);
  } catch (err) {
    const container = document.getElementById('feed-container');
    container.innerHTML = `<p class="error-msg">Could not load feeds: ${esc(err.message)}</p>`;
    console.error('Feed load failed:', err);
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('service-worker.js').catch(err => {
      console.warn('SW registration failed:', err);
    });
  }
}

document.addEventListener('DOMContentLoaded', main);
