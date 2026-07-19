import feedparser
import time

# Real AI/Tech RSS sources — swap/add as you like
FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.technologyreview.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "http://export.arxiv.org/rss/cs.AI",
]

_cache = {"articles": [], "last_fetch": 0}
CACHE_TTL = 60 * 15  # refresh every 15 minutes


def fetch_articles(limit_per_feed=5, force=False):
    """Pulls fresh articles from RSS feeds, with a 15-min cache to avoid hammering sources."""
    now = time.time()
    if not force and _cache["articles"] and (now - _cache["last_fetch"] < CACHE_TTL):
        return _cache["articles"]

    articles = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            source_name = feed.feed.get("title", url)
            for entry in feed.entries[:limit_per_feed]:
                articles.append({
                    "title": entry.get("title", "").strip(),
                    "summary": (entry.get("summary", "") or "")[:400].strip(),
                    "source": source_name,
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                })
        except Exception as e:
            print(f"[scraper] Failed to fetch {url}: {e}")

    if articles:
        _cache["articles"] = articles
        _cache["last_fetch"] = now

    return _cache["articles"]


if __name__ == "__main__":
    # Quick manual test: python scraper.py
    results = fetch_articles(force=True)
    print(f"Fetched {len(results)} articles\n")
    for a in results[:5]:
        print(f"- {a['title']}  ({a['source']})")