"""Cross-outlet corroboration and claim checking.

No AI is involved here, so nothing in this module can be made up: it only counts which independent
outlets are reporting the same story, and looks for matching fact-checks. The results are written to
each article (annotate) or handed to the chat agent as evidence (check_claim).
"""
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Callable, Dict, List, Optional

import sources

# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------
_STOP = set(
    "a an the and or but of to in on at for from by with as is are was were be been it its this that these those "
    "he she they his her their our your you we i not no new says say said will would could should may might can "
    "after before over under into about amid more than also just up out off how why what who when where which "
    "while has have had do does did".split()
)
_OUTLET_NOISE = {"the", "news", "english", "online", "rss", "feed"}
_OUTLET_SPLIT = re.compile(r"\s[-\u2013\u2014|]\s|:")
_TRAILING_OUTLET = re.compile(r"\s[-\u2013\u2014|]\s[^-\u2013\u2014|]{2,40}$")


def _tokens(text: str) -> set:
    text = _TRAILING_OUTLET.sub("", text or "")
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in _STOP or (len(w) < 3 and not w.isdigit()):
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.add(w)
    return out


def same_story(a: str, b: str) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    inter = len(ta & tb)
    if inter < 3:
        return False
    jaccard = inter / len(ta | tb)
    overlap = inter / min(len(ta), len(tb))
    return jaccard >= 0.4 or (inter >= 4 and overlap >= 0.7)


def outlet_key(source: str) -> str:
    """'BBC News - World' and 'BBC' count as one outlet. Collisions only ever undercount, which is the safe error."""
    first = _OUTLET_SPLIT.split((source or "").strip())[0].lower()
    words = [w for w in re.findall(r"[a-z0-9]+", first) if w not in _OUTLET_NOISE]
    return " ".join(words)


def outlet_name(source: str) -> str:
    return _OUTLET_SPLIT.split((source or "").strip())[0].strip() or "Unknown"


def _relevance(query_tokens: set, text: str) -> float:
    if not query_tokens:
        return 0.0
    return len(query_tokens & _tokens(text)) / len(query_tokens)


def score_for(count: int) -> float:
    """A simple corroboration score, NOT a probability that the story is true."""
    return {0: 0.0, 1: 0.3, 2: 0.6, 3: 0.8}.get(count, 0.9)


def _default_fetch(query: str, limit: int = 25, max_age_days: int = 7) -> List[dict]:
    return sources.fetch_topic_articles(query, limit=limit, max_age_days=max_age_days)


# ---------------------------------------------------------------------------
# 1) Outlet counting for stored articles
# ---------------------------------------------------------------------------
def _search_query(title: str) -> str:
    t = _TRAILING_OUTLET.sub("", title or "")
    t = re.sub(r"[^\w\s'-]", " ", t)
    return " ".join(t.split())[:110]


def annotate(targets: List[dict], pool: Optional[List[dict]] = None, fetch: Optional[Callable] = None, *,
             online: bool = True, budget_s: float = 15.0, max_online: int = 30, workers: int = 8) -> List[dict]:
    """Adds a.corroboration = {status, count, outlets, online_checked} to each target article.

    status: 'corroborated' (2+ independent outlets), 'single_source' (checked online, only one found),
            'unchecked' (only one outlet seen and the online check did not run or did not finish).
    """
    fetch = fetch or _default_fetch
    pool = pool if pool is not None else targets
    found: Dict[int, Dict[str, str]] = {}

    for a in targets:
        outlets = {outlet_key(a.get("source")): outlet_name(a.get("source"))}
        for b in pool:
            if b is not a and same_story(a.get("title", ""), b.get("title", "")):
                outlets.setdefault(outlet_key(b.get("source")), outlet_name(b.get("source")))
        found[id(a)] = outlets

    checked: set = set()
    if online:
        todo = [a for a in targets if len(found[id(a)]) < 3][:max_online]

        def lookup(article: dict) -> Dict[str, str]:
            res: Dict[str, str] = {}
            for r in fetch(_search_query(article.get("title", ""))):
                if same_story(article.get("title", ""), r.get("title", "")):
                    res.setdefault(outlet_key(r.get("source")), outlet_name(r.get("source")))
            return res

        ex = ThreadPoolExecutor(max_workers=workers)
        futs = {ex.submit(lookup, a): a for a in todo}
        done, _ = wait(futs, timeout=budget_s)
        ex.shutdown(wait=False, cancel_futures=True)
        for f in done:
            try:
                for k, name in f.result().items():
                    found[id(futs[f])].setdefault(k, name)
                checked.add(id(futs[f]))
            except Exception as e:  # one failed lookup must not break the batch
                print(f"[verify] lookup failed: {e}")

    for a in targets:
        outlets = found[id(a)]
        count = len(outlets)
        was_checked = id(a) in checked
        status = "corroborated" if count >= 2 else ("single_source" if was_checked else "unchecked")
        a["corroboration"] = {"status": status, "count": count, "outlets": sorted(outlets.values()),
                              "online_checked": was_checked}
    return targets


# ---------------------------------------------------------------------------
# 2) Claim checking for the chat agent
# ---------------------------------------------------------------------------
FACT_CHECK_FEEDS = {
    "Dubawa": "https://dubawa.org/feed/",
    "FactCheckHub": "https://factcheckhub.com/feed/",
    "Africa Check": "https://africacheck.org/feed",
    "ICIR": "https://www.icirnigeria.org/feed/",
}
_FACT_WORDS = re.compile(r"fact.?check|false|misleading|fake|hoax|debunk|fabricat|not true|no evidence|"
                         r"unfounded|claim|rumou?r|did not|doesn't|isn't|untrue|baseless", re.I)
_FEED_TTL = 60 * 15
_feed_cache: Dict[str, tuple] = {}
_feed_lock = threading.Lock()


def fetch_feed_items(url: str, source_name: str) -> List[dict]:
    now = time.time()
    with _feed_lock:
        hit = _feed_cache.get(url)
    if hit and now - hit[0] < _FEED_TTL:
        return hit[1]
    feed = sources._parse_feed(url)
    items = []
    for e in feed.entries[:40]:
        g = lambda k, d="": sources._entry_get(e, k, d) or d
        items.append({"title": g("title").strip(), "summary": sources._clean_html(g("summary") or g("description"))[:400],
                      "link": g("link"), "published": g("published") or g("updated"), "source": source_name})
    with _feed_lock:
        _feed_cache[url] = (now, items)
    return items


def auto_query(claim: str, max_words: int = 8) -> str:
    seen, words = set(), []
    for w in re.findall(r"[A-Za-z0-9']+", claim):
        lw = w.lower()
        if lw in _STOP or (len(lw) < 3 and not lw.isdigit()) or lw in seen:
            continue
        seen.add(lw)
        words.append(w)
        if len(words) >= max_words:
            break
    return " ".join(words)


def check_claim(claim: str, query: Optional[str] = None, *, fetch: Optional[Callable] = None,
                feed_fetch: Optional[Callable] = None, budget_s: float = 14.0) -> dict:
    """Looks for (a) independent outlets covering the claim and (b) fact-checks about it. Returns evidence only."""
    fetch = fetch or _default_fetch
    feed_fetch = feed_fetch or fetch_feed_items
    claim = " ".join((claim or "").split())[:600]
    if len(claim) < 8:
        return {"ok": False, "error": "Need the claim or message text to check."}
    q = " ".join((query or "").split())[:120] or auto_query(claim)
    qtok = _tokens(q)
    if len(qtok) < 2:
        return {"ok": False, "error": "Could not find enough keywords in that claim to search."}

    ex = ThreadPoolExecutor(max_workers=6)
    f_cov = ex.submit(fetch, q, 25, 14)
    f_fc = ex.submit(fetch, q + " fact check", 25, 60)
    f_feeds = {name: ex.submit(feed_fetch, url, name) for name, url in FACT_CHECK_FEEDS.items()}
    wait([f_cov, f_fc, *f_feeds.values()], timeout=budget_s)
    ex.shutdown(wait=False, cancel_futures=True)

    def result(f):
        try:
            return f.result(timeout=0) if f.done() else []
        except Exception as e:
            print(f"[verify] check_claim source failed: {e}")
            return []

    # (a) coverage
    coverage, outlets = [], {}
    for r in result(f_cov):
        rel = _relevance(qtok, r.get("title", ""))
        if rel >= 0.5:
            outlets.setdefault(outlet_key(r.get("source")), outlet_name(r.get("source")))
            coverage.append({"title": r["title"][:160], "source": r.get("source", ""), "published": r.get("published", ""),
                             "link": r.get("link", ""), "relevance": round(rel, 2)})
    coverage.sort(key=lambda x: -x["relevance"])

    # (b) fact-checks: direct fact-checker feeds first (links can be opened), then a search for older ones
    checks, seen_titles = [], set()
    for name, f in f_feeds.items():
        for it in result(f):
            rel = _relevance(qtok, it["title"] + " " + it.get("summary", ""))
            if rel >= 0.5 and it["title"] not in seen_titles:
                seen_titles.add(it["title"])
                checks.append({"title": it["title"][:160], "source": name, "published": it.get("published", ""),
                               "summary": it.get("summary", "")[:300], "link": it.get("link", ""),
                               "link_readable": True, "relevance": round(rel, 2)})
    for r in result(f_fc):
        title = r.get("title", "")
        rel = _relevance(qtok, title)
        if rel >= 0.5 and _FACT_WORDS.search(title) and title not in seen_titles:
            seen_titles.add(title)
            checks.append({"title": title[:160], "source": r.get("source", ""), "published": r.get("published", ""),
                           "link": r.get("link", ""), "link_readable": False, "relevance": round(rel, 2)})
    checks.sort(key=lambda x: (-x["link_readable"], -x["relevance"]))

    if checks:
        signal = "fact_check_found"
    elif len(outlets) >= 3:
        signal = "multiple_outlets"
    elif outlets:
        signal = "limited_coverage"
    else:
        signal = "nothing_found"
    return {"ok": True, "claim": claim, "search_query": q, "signal": signal,
            "independent_outlets": sorted(outlets.values()), "coverage": coverage[:6], "fact_checks": checks[:5],
            "note": ("Evidence only. Finding no coverage does NOT prove a claim is false: it may be very recent, local "
                     "or only on WhatsApp. A fact-check headline is not a verdict until you have read it.")}
