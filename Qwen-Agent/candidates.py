"""Finds breach stories worth turning into cards.

Reads security-news feeds, keeps stories that look like real incidents, groups the same story
across outlets, and ranks them by how many independent outlets cover it. It never writes
anything: you pick the links, then POST them to /breaches/draft.
"""
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Dict, List, Optional, Set

import sources
import verify

# Feeds can be changed here without touching anything else. A feed that fails is skipped.
SECURITY_FEEDS = [
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
    ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
    ("SecurityWeek", "https://www.securityweek.com/feed/"),
    ("Cybersecurity Dive", "https://www.cybersecuritydive.com/feeds/news/"),
    ("Dark Reading", "https://www.darkreading.com/rss.xml"),
    ("The Record", "https://therecord.media/feed"),
]

BREACH = re.compile(
    r"\b(breach(?:ed|es)?|hack(?:ed|ers?|s)?|stolen|steal(?:s|ing)?|heist|ransomware|data leak(?:ed|s)?|"
    r"leak(?:ed|s)|exposed|compromis(?:e|ed)|cyber[- ]?attack|supply[- ]chain attack|zero-day|"
    r"extortion|data theft|exfiltrat\w+|intrusion)\b", re.I)
NOISE = re.compile(r"\b(webinar|podcast|sponsored|patch tuesday|how to|best practices|survey|report finds|"
                   r"guide|whitepaper|week in review|newsletter|podcast)\b", re.I)
BIG = re.compile(r"\b\d[\d.,]*\s?(?:billion|million|bn|m)\b|\bmillions?\b|\bbillions?\b", re.I)

CACHE_TTL = 60 * 15
_cache: Dict[str, tuple] = {}
_lock = threading.Lock()


def _parse_date(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    try:
        d = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _load_feed(name: str, url: str) -> List[dict]:
    now = time.time()
    with _lock:
        hit = _cache.get(url)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]
    items = verify.fetch_feed_items(url, name)
    with _lock:
        _cache[url] = (now, items)
    return items


def looks_like_incident(item: dict) -> bool:
    title = item.get("title", "")
    if not title or NOISE.search(title):
        return False
    return bool(BREACH.search(title) or (BREACH.search(item.get("summary", "")) and BIG.search(title + " " + item.get("summary", ""))))


def find_candidates(known_urls: Set[str], *, days: int = 7, min_outlets: int = 1, limit: int = 15,
                    feeds: Optional[List[tuple]] = None, load: Callable = _load_feed,
                    now: Optional[datetime] = None) -> Dict:
    feeds = feeds or SECURITY_FEEDS
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    failed: List[str] = []

    def one(feed):
        try:
            return feed[0], load(feed[0], feed[1])
        except Exception:
            failed.append(feed[0])
            return feed[0], []

    with ThreadPoolExecutor(max_workers=len(feeds)) as pool:
        results = list(pool.map(one, feeds))

    stories: List[dict] = []
    for outlet, items in results:
        for it in items:
            when = _parse_date(it.get("published", ""))
            if not it.get("link") or (when and when < cutoff) or not looks_like_incident(it):
                continue
            stories.append({"outlet": outlet, "title": it["title"], "url": it["link"], "when": when})

    clusters: List[List[dict]] = []
    for st in sorted(stories, key=lambda s: s["when"] or cutoff, reverse=True):
        for c in clusters:
            if verify.same_story(c[0]["title"], st["title"]):
                c.append(st)
                break
        else:
            clusters.append([st])

    out = []
    for c in clusters:
        urls = {s["url"] for s in c}
        if urls & known_urls:
            continue  # already used as a source for a card
        by_outlet: Dict[str, dict] = {}
        for s in c:
            by_outlet.setdefault(s["outlet"], s)
        outlets = list(by_outlet.values())
        if len(outlets) < min_outlets:
            continue
        newest = max((s["when"] for s in c if s["when"]), default=None)
        out.append({
            "title": c[0]["title"],
            "outlets": len(outlets),
            "corroborated": len(outlets) >= 2,
            "big_numbers": bool(BIG.search(" ".join(s["title"] for s in c))),
            "newest": newest.isoformat() if newest else None,
            "links": [{"outlet": s["outlet"], "title": s["title"], "url": s["url"]} for s in outlets],
            "draft_urls": [s["url"] for s in outlets[:3]],
        })
    out.sort(key=lambda x: (x["outlets"], x["big_numbers"], x["newest"] or ""), reverse=True)
    return {"candidates": out[:limit], "feeds_failed": sorted(set(failed)), "checked_feeds": len(feeds)}
