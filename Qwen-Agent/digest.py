"""Builds and stores a topic digest: fetch headlines -> save new stories -> summarise with Groq."""
import time
from typing import Callable, Dict, List, Optional

import sources
import verify
from config import Settings
from llm import GroqClient, LLMError
from rows import to_topic_row
from store import Store

DIGEST_SYSTEM = (
    "You write short briefings for a news app. Use ONLY the numbered headlines you are given. "
    "Do not add facts, numbers, names or causes that are not in them, and say so if the headlines "
    "are thin. No emoji. Output markdown: one or two sentences of overview, then 3 to 5 bullets "
    "(each ends with the outlet in parentheses), under 140 words in total."
)


def headline_list(articles: List[dict]) -> List[dict]:
    return [{"title": a["title"], "source": a.get("source", ""), "link": a.get("link", ""),
             "published": a.get("published", "")} for a in articles]


def fallback_digest(topic: str, articles: List[dict]) -> str:
    lines = [f"Latest headlines on **{topic}**:", ""]
    lines += [f"- {a['title']} ({a.get('source') or 'unknown source'})" for a in articles[:5]]
    return "\n".join(lines)


def build_digest_text(llm: GroqClient, topic: str, articles: List[dict], settings: Settings):
    """Returns (markdown, model_name). Falls back to a plain headline list if Groq is unavailable."""
    numbered = "\n".join(f"{i}. {a['title']} ({a.get('source') or 'unknown'})" for i, a in enumerate(articles[:8], 1))
    try:
        out = llm.complete(
            [{"role": "system", "content": DIGEST_SYSTEM},
             {"role": "user", "content": f"Topic: {topic}\nHeadlines:\n{numbered}"}],
            model=settings.fast_model, max_tokens=450, temperature=0.2)
        text = out["content"].strip()
        if text:
            return text, out["model"]
    except LLMError as e:
        print(f"[digest] Groq unavailable for '{topic}': {e}")
    return fallback_digest(topic, articles), "headlines-only"


def refresh_topic(store: Store, llm: GroqClient, settings: Settings, topic: dict,
                  fetch: Optional[Callable] = None) -> Dict:
    """topic = {"slug", "topic", "query"}. Safe to call repeatedly: only unseen stories are stored
    and the digest is only regenerated when something new arrived (or none exists yet)."""
    fetch = fetch or sources.fetch_topic_articles
    slug, name, query = topic["slug"], topic["topic"], topic.get("query") or topic["topic"]
    articles = fetch(query, topic=name, limit=settings.articles_per_topic, lang=settings.news_lang,
                     region=settings.news_region, max_age_days=settings.topic_max_age_days)
    category = f"topic-{slug}"
    seen = store.existing_titles([a["title"] for a in articles], category) if articles else set()
    fresh = [a for a in articles if a["title"] not in seen]
    if fresh:
        verify.annotate(fresh, pool=articles, online=False)  # local only: the batch already spans many outlets
    inserted = store.insert_articles([to_topic_row(a, slug) for a in fresh]) if fresh else 0

    digest_saved = False
    model = ""
    if articles and (fresh or store.latest_digest(slug) is None):
        text, model = build_digest_text(llm, name, fresh or articles, settings)
        store.save_digest(slug, name, text, headline_list(fresh or articles), model)
        digest_saved = True
    store.touch_topic(slug)
    return {"slug": slug, "fetched": len(articles), "new": inserted, "digest_saved": digest_saved,
            "model": model, "articles": articles}


def refresh_all(store: Store, llm: GroqClient, settings: Settings, sleep=time.sleep) -> Dict:
    """Used by the scheduled job: one fetch + at most one Groq call per distinct topic."""
    summary = {"topics": 0, "ok": 0, "failed": 0, "new_articles": 0, "errors": []}
    for t in store.distinct_topics():
        summary["topics"] += 1
        try:
            r = refresh_topic(store, llm, settings, t)
            summary["ok"] += 1
            summary["new_articles"] += r["new"]
        except Exception as e:  # one broken topic must not stop the rest
            summary["failed"] += 1
            summary["errors"].append(f"{t.get('slug')}: {e}")
        sleep(settings.digest_pause_s)
    return summary
