# NewsKit — Personal News & 就活 Aggregator

A zero-cost, iPhone-first PWA that aggregates RSS/Atom feeds across three categories:

| Category | Content |
|---|---|
| **Tech Global** | Global technology news (English) |
| **Tech Japan** | Japanese technology news (Japanese) |
| **就活 / 転職** | Japan job-hunting & career content |

Feed data refreshes every 3 hours via GitHub Actions. The static site is served by GitHub Pages at zero cost.

---

## Set up

### 1. Fork / create the repo

Create a **private** GitHub repo (keeps your read history in localStorage — not in the repo — so a public repo is also fine if you prefer).

### 2. Enable GitHub Pages

Go to **Settings → Pages** and set source to **GitHub Actions** (or the `main` branch, `/public` folder).

### 3. First run

Trigger the workflow manually once so `feed.json` is populated before you visit the site:

**Actions → Refresh Feeds → Run workflow**

### 4. Install on iPhone

Open the GitHub Pages URL in **Safari**, then:

> **Share → Add to Home Screen**

The app launches in standalone mode (no browser chrome).

---

## Manage sources

Edit [`sources.yaml`](sources.yaml) — add, remove, or rename feeds. One entry per source:

```yaml
tech_global:
  - name: My Blog
    url: https://example.com/feed.xml
```

Push the change. The next scheduled run (or a manual trigger) picks it up. No code change needed.

---

## Local development

```bash
pip install -r requirements.txt
python scripts/fetch_feeds.py        # generates public/data/feed.json
# then open public/index.html in a browser (or serve with: python -m http.server -d public)
```

To regenerate icons (needed only once, already committed):

```bash
python scripts/generate_icons.py
```

---

## Architecture

```
GitHub Actions (cron every 3h)
  └─ fetch_feeds.py reads sources.yaml
  └─ writes public/data/feed.json
  └─ commits & pushes

GitHub Pages serves public/
  └─ index.html + app.js + styles.css
  └─ data/feed.json  ← fetched by the browser

iPhone Safari (PWA)
  └─ service worker: shell cached, feed network-first
  └─ localStorage: read state + category toggles
```

Total monthly cost: **$0**.
