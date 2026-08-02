import feedparser
import re
import time

# Feeds organized by category. Add more sources to any list freely —
# all are free, public RSS feeds, no API key needed.
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

_cache = {}  # keyed by category, each value: {"articles": [...], "last_fetch": ts}
CACHE_TTL = 60 * 15  # 15 minutes


def _clean_html(raw_html: str) -> str:
    """Helper to strip HTML tags and extra whitespaces from RSS summaries."""
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return ' '.join(clean_text.split())


def fetch_articles(category="tech", limit_per_feed=5, force=False):
    """Pulls fresh articles from RSS feeds for a given category, with a
    15-min cache per category to avoid hammering sources.
    Pass category='all' to fetch every category's feeds in one call."""

    if category == "all":
        combined = []
        for cat in FEEDS_BY_CATEGORY:
            combined.extend(fetch_articles(category=cat, limit_per_feed=limit_per_feed, force=force))
        return combined

    if category not in FEEDS_BY_CATEGORY:
        print(f"[scraper] Unknown category '{category}', falling back to 'tech'")
        category = "tech"

    now = time.time()
    cached = _cache.get(category)
    if not force and cached and (now - cached["last_fetch"] < CACHE_TTL):
        return cached["articles"]

    articles = []
    for url in FEEDS_BY_CATEGORY[category]:
        try:
            feed = feedparser.parse(url)
            source_name = feed.feed.get("title", url).replace("RSS Feed", "").strip()

            for entry in feed.entries[:limit_per_feed]:
                raw_summary = entry.get("summary", "") or entry.get("description", "")
                clean_summary = _clean_html(raw_summary)[:400].strip()

                articles.append({
                    "title": entry.get("title", "").strip(),
                    "summary": clean_summary,
                    "source": source_name,
                    "link": entry.get("link", ""),
                    "published": entry.get("published", entry.get("updated", "")),
                    "category": category,  # Guaranteed 'tech', 'geopolitics', or 'startups'
                })
        except Exception as e:
            print(f"[scraper] Failed to fetch {url}: {e}")

    if articles:
        _cache[category] = {"articles": articles, "last_fetch": now}

    return articles


if __name__ == "__main__":
    for cat in FEEDS_BY_CATEGORY:
        results = fetch_articles(category=cat, force=True)
        print(f"\n[{cat}] Fetched {len(results)} articles")
        for a in results[:3]:
            print(f"- {a['title']}  ({a['source']})")