"""
Fetches RSS/Atom feeds defined in sources.yaml and writes public/data/feed.json.
Run locally or via GitHub Actions on a schedule.
"""

import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import mktime

import feedparser
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SOURCES_FILE = REPO_ROOT / "sources.yaml"
OUTPUT_FILE = REPO_ROOT / "public" / "data" / "feed.json"

PER_SOURCE_CAP = 10
PER_CATEGORY_CAP = 50
SUMMARY_MAX_CHARS = 280
FETCH_TIMEOUT = 10
USER_AGENT = "NewsAggregator/1.0 (personal RSS reader; +https://github.com)"


def load_sources():
    with open(SOURCES_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate(text, max_chars):
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def item_id(url):
    return hashlib.sha1(url.encode()).hexdigest()


def parse_published(entry):
    """Return ISO 8601 UTC string, or None if unparseable."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            dt = datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass
    return None


def fetch_source(source):
    """Fetch one feed. Returns list of normalized item dicts."""
    name = source["name"]
    url = source["url"]
    log.info("Fetching %s (%s)", name, url)
    try:
        feed = feedparser.parse(
            url,
            request_headers={"User-Agent": USER_AGENT},
            agent=USER_AGENT,
        )
        if feed.bozo and not feed.entries:
            log.warning("Bozo feed with no entries: %s — %s", name, feed.bozo_exception)
            return []
    except Exception as exc:
        log.warning("Failed to fetch %s: %s", name, exc)
        return []

    items = []
    for entry in feed.entries[:PER_SOURCE_CAP * 2]:
        link = getattr(entry, "link", None)
        title = strip_html(getattr(entry, "title", None) or "")
        if not link or not title:
            continue

        summary_raw = (
            getattr(entry, "summary", None)
            or (entry.content[0].value if getattr(entry, "content", None) else None)
            or ""
        )
        summary = truncate(strip_html(summary_raw), SUMMARY_MAX_CHARS)

        items.append({
            "id": item_id(link),
            "title": title,
            "url": link,
            "source": name,
            "published": parse_published(entry),
            "summary": summary,
        })

    items.sort(key=lambda x: x["published"] or "", reverse=True)
    return items[:PER_SOURCE_CAP]


def dedup_items(items):
    """
    Deduplicate by id (SHA1 of URL). When two entries share the same id
    (same URL from different source feeds), keep the one with richer data.
    Secondary dedup: (normalized_title, source_domain) per plan spec.
    """
    seen_ids = {}
    for item in items:
        existing = seen_ids.get(item["id"])
        if existing is None or (item["published"] or "") > (existing["published"] or ""):
            seen_ids[item["id"]] = item

    # Secondary dedup by (normalized_title, source_domain)
    seen_title_domain = {}
    result = []
    for item in seen_ids.values():
        from urllib.parse import urlparse
        domain = urlparse(item["url"]).netloc
        norm_title = re.sub(r"\s+", " ", item["title"].lower().strip())
        key = (norm_title, domain)
        existing = seen_title_domain.get(key)
        if existing is None or (item["published"] or "") > (existing["published"] or ""):
            seen_title_domain[key] = item

    return list(seen_title_domain.values())


def main():
    sources = load_sources()
    categories = {}

    for cat_key, source_list in sources.items():
        if not source_list:
            categories[cat_key] = []
            continue

        all_items = []
        for source in source_list:
            all_items.extend(fetch_source(source))

        deduped = dedup_items(all_items)
        deduped.sort(key=lambda x: x["published"] or "", reverse=True)
        categories[cat_key] = deduped[:PER_CATEGORY_CAP]
        log.info("Category %s: %d items after dedup", cat_key, len(categories[cat_key]))

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": categories,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    log.info("Written to %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
