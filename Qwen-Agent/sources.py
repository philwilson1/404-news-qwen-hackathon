"""News sources.

* FEEDS_BY_CATEGORY: your original fixed category feeds (tech / geopolitics / startups).
* fetch_topic_articles(): NEW. Pulls headlines for ANY topic from the Google News RSS
  search feed. Free, no API key.
"""
import calendar
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests

FEEDS_BY_CATEGORY = {
    "tech": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.technologyreview.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "http://export.arxiv.org/rss/cs.AI",
    ],
    "geopolitics": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.politico.com/rss/politicopicks.xml",
    ],
    "startups": [
        "https://techcrunch.com/category/startups/feed/",
        "https://venturebeat.com/feed/",
        "https://www.crunchbase.com/feed",
        "https://sifted.eu/feed",
    ],
}

USER_AGENT = "Mozilla/5.0 (compatible; 404NewsBot/2.0; +https://404-news-qwen-hackathon.vercel.app)"
CACHE_TTL = 60 * 15
TOPIC_CACHE_TTL = 60 * 10
FEED_TIMEOUT = 12

_cache: Dict[str, Dict[str, Any]] = {}
_topic_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()


def _clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return " ".join(text.split())


def _parse_feed(url: str):
    """Download with a hard timeout (feedparser.parse(url) has none and can hang a worker)."""
    import feedparser  # imported lazily so the rest of the module is importable without it

    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=FEED_TIMEOUT)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def _entry_get(entry, key: str, default=None):
    getter = getattr(entry, "get", None)
    return getter(key, default) if getter else getattr(entry, key, default)


def _entry_datetime(entry) -> Optional[datetime]:
    parsed = _entry_get(entry, "published_parsed") or _entry_get(entry, "updated_parsed")
    if not parsed:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


# --------------------------------------------------------------------------
# Fixed category feeds (original behaviour)
# --------------------------------------------------------------------------
def fetch_articles(category: str = "tech", limit_per_feed: int = 5, force: bool = False) -> List[dict]:
    if category == "all":
        combined: List[dict] = []
        for cat in FEEDS_BY_CATEGORY:
            combined.extend(fetch_articles(cat, limit_per_feed, force))
        return combined
    if category not in FEEDS_BY_CATEGORY:
        category = "tech"

    now = time.time()
    with _cache_lock:
        cached = _cache.get(category)
    if not force and cached and now - cached["last_fetch"] < CACHE_TTL:
        return cached["articles"]

    articles: List[dict] = []
    for url in FEEDS_BY_CATEGORY[category]:
        try:
            feed = _parse_feed(url)
            source_name = (_entry_get(feed.feed, "title", url) or url).replace("RSS Feed", "").strip()
            for entry in feed.entries[:limit_per_feed]:
                raw = _entry_get(entry, "summary", "") or _entry_get(entry, "description", "")
                articles.append({
                    "title": (_entry_get(entry, "title", "") or "").strip(),
                    "summary": _clean_html(raw)[:400].strip(),
                    "source": source_name,
                    "link": _entry_get(entry, "link", ""),
                    "published": _entry_get(entry, "published", _entry_get(entry, "updated", "")),
                    "category": category,
                })
        except Exception as e:  # one dead feed must not kill the batch
            print(f"[sources] failed to fetch {url}: {e}")
    if articles:
        with _cache_lock:
            _cache[category] = {"articles": articles, "last_fetch": now}
    return articles


# --------------------------------------------------------------------------
# Any-topic search (Google News RSS)
# --------------------------------------------------------------------------
def google_news_url(query: str, lang: str = "en", region: str = "NG", max_age_days: int = 7) -> str:
    q = f"{query} when:{max_age_days}d" if max_age_days else query
    return (f"https://news.google.com/rss/search?q={quote_plus(q)}"
            f"&hl={lang}-{region}&gl={region}&ceid={region}:{lang}")


def _split_title_source(title: str, source: str) -> tuple:
    """Google News titles look like 'Headline - Outlet'. Strip the outlet suffix."""
    title = title.strip()
    if source and title.endswith(f" - {source}"):
        return title[: -(len(source) + 3)].strip(), source
    if not source and " - " in title:
        head, _, tail = title.rpartition(" - ")
        if head and len(tail) <= 40:
            return head.strip(), tail.strip()
    return title, source or "Google News"


def _norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def entry_to_topic_article(entry, topic: str) -> Optional[dict]:
    raw_title = (_entry_get(entry, "title", "") or "").strip()
    if not raw_title:
        return None
    src = _entry_get(entry, "source", None)
    source = ""
    if src is not None:
        source = (_entry_get(src, "title", "") or "").strip()
    title, source = _split_title_source(raw_title, source)

    summary = _clean_html(_entry_get(entry, "summary", "") or _entry_get(entry, "description", ""))
    # Google's description is just the headline + outlet repeated; it adds nothing.
    if not summary or _norm_title(summary).startswith(_norm_title(title)[:40]):
        summary = ""
    when = _entry_datetime(entry)
    return {
        "title": title,
        "summary": summary[:400],
        "source": source,
        "link": _entry_get(entry, "link", ""),
        "published": _entry_get(entry, "published", "") or (when.isoformat() if when else ""),
        "published_dt": when,
        "category": "topic",
        "topic": topic,
    }


def select_articles(articles: List[dict], limit: int, max_age_days: int, per_source: int = 2) -> List[dict]:
    """Drop stale + duplicate headlines, newest first, and keep a mix of outlets."""
    cutoff = None
    if max_age_days:
        cutoff = datetime.now(timezone.utc).timestamp() - max_age_days * 86400
    seen, fresh = set(), []
    for a in articles:
        key = _norm_title(a["title"])
        if not key or key in seen:
            continue
        dt = a.get("published_dt")
        if cutoff and dt and dt.timestamp() < cutoff:
            continue
        seen.add(key)
        fresh.append(a)
    fresh.sort(key=lambda a: a["published_dt"].timestamp() if a.get("published_dt") else 0, reverse=True)

    picked, counts, overflow = [], {}, []
    for a in fresh:
        n = counts.get(a["source"], 0)
        if n < per_source:
            picked.append(a)
            counts[a["source"]] = n + 1
        else:
            overflow.append(a)
    picked.extend(overflow)  # only used if there were too few distinct outlets
    return picked[:limit]


def fetch_topic_articles(query: str, *, topic: Optional[str] = None, limit: int = 8, lang: str = "en",
                         region: str = "NG", max_age_days: int = 7, force: bool = False) -> List[dict]:
    key = f"{query.lower()}|{lang}|{region}|{max_age_days}|{limit}"
    now = time.time()
    with _cache_lock:
        cached = _topic_cache.get(key)
    if not force and cached and now - cached["t"] < TOPIC_CACHE_TTL:
        return cached["articles"]

    feed = _parse_feed(google_news_url(query, lang, region, max_age_days))
    topic_name = topic or query
    items = [a for a in (entry_to_topic_article(e, topic_name) for e in feed.entries) if a]
    chosen = select_articles(items, limit, max_age_days)
    with _cache_lock:
        _topic_cache[key] = {"t": now, "articles": chosen}
    return chosen
