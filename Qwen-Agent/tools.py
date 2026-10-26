"""Tools the chat agent can call. This is what turns "keep me in the loop on X" into
a real subscription instead of just a chat reply."""
import json
from typing import Any, Callable, Dict, List, Optional

import digest
import reader
import sources
from config import Settings
from llm import GroqClient
from store import Store, TopicLimitError
from topics import normalize_topic

TOOL_SCHEMAS: List[dict] = [
    {"type": "function", "function": {
        "name": "follow_topic",
        "description": "Start keeping the user in the loop on a topic. Use when they ask to follow, track, "
                       "monitor, watch, or be kept updated on a subject. Fetches the first stories and saves a "
                       "digest that refreshes automatically.",
        "parameters": {"type": "object", "properties": {
            "topic": {"type": "string", "description": "Short topic name, e.g. 'quantum computing'"}},
            "required": ["topic"]}}},
    {"type": "function", "function": {
        "name": "unfollow_topic",
        "description": "Stop following a topic the user no longer wants updates on.",
        "parameters": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]}}},
    {"type": "function", "function": {
        "name": "list_followed_topics",
        "description": "List the topics the user currently follows.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_category_news",
        "description": "Current stories WITH short summaries from curated publisher feeds (TechCrunch, MIT Technology "
                       "Review, Ars Technica, BBC, Al Jazeera, VentureBeat and others). Use for AI and technology "
                       "(tech), startups and funding (startups), world affairs (geopolitics), and health and medicine "
                       "(health). Best choice for "
                       "'what is trending in AI/tech' style questions.",
        "parameters": {"type": "object", "properties": {
            "category": {"type": "string", "enum": ["tech", "startups", "geopolitics", "health"]},
            "limit": {"type": "integer", "description": "1-8, default 6"}},
            "required": ["category"]}}},
    {"type": "function", "function": {
        "name": "get_topic_news",
        "description": "Get current headlines on ANY topic right now (does not follow it). Use for 'what is new "
                       "on X', or whenever an answer depends on recent events.",
        "parameters": {"type": "object", "properties": {
            "topic": {"type": "string"},
            "limit": {"type": "integer", "description": "1-8, default 6"}},
            "required": ["topic"]}}},
    {"type": "function", "function": {
        "name": "read_article",
        "description": "Open one news article from its link and read its text, so you can give real detail on a "
                       "single story. Use when the user asks for more detail, 'tell me more', a deeper explanation "
                       "or a summary of a specific story. Pass the link returned by a news tool or shown in your "
                       "earlier answer. Never invent a link.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "The article link (http or https)"}},
            "required": ["url"]}}},
]


def _compact(articles: List[dict], n: int) -> List[dict]:
    out = []
    for a in articles[:n]:
        item = {"title": a["title"][:140], "source": a.get("source", ""), "published": a.get("published", ""),
                "link": a.get("link", "")}
        if a.get("summary"):
            item["summary"] = str(a["summary"])[:300]
        out.append(item)
    return out


def _round_robin(items: List[dict], n: int) -> List[dict]:
    """Mix outlets so one publisher cannot fill the whole answer."""
    groups: Dict[str, List[dict]] = {}
    for a in items:
        groups.setdefault(a.get("source", ""), []).append(a)
    out: List[dict] = []
    while len(out) < n and any(groups.values()):
        for g in groups.values():
            if g and len(out) < n:
                out.append(g.pop(0))
    return out


class ToolRunner:
    def __init__(self, store: Store, llm: GroqClient, settings: Settings, user_id: str,
                 fetch: Optional[Callable] = None, fetch_category: Optional[Callable] = None,
                 read: Optional[Callable] = None):
        self.store, self.llm, self.s, self.user_id = store, llm, settings, user_id
        self.fetch = fetch or sources.fetch_topic_articles
        self.read = read or reader.fetch_article_text
        self.fetch_category = fetch_category or (lambda cat: sources.fetch_articles(category=cat, limit_per_feed=4))

    def run(self, name: str, raw_args: str) -> Dict[str, Any]:
        """Returns {"result": dict_for_the_model, "event": dict_for_the_ui_or_None}."""
        try:
            args = json.loads(raw_args or "{}")
            if not isinstance(args, dict):
                raise ValueError
        except ValueError:
            return {"result": {"ok": False, "error": "Arguments were not valid JSON."}, "event": None}
        handler = {"follow_topic": self._follow, "unfollow_topic": self._unfollow,
                   "list_followed_topics": self._list, "get_topic_news": self._news,
                   "get_category_news": self._category, "read_article": self._read}.get(name)
        if not handler:
            return {"result": {"ok": False, "error": f"Unknown tool {name}."}, "event": None}
        try:
            return handler(args)
        except Exception as e:  # never let a tool crash the chat stream
            print(f"[tools] {name} failed: {e}")
            return {"result": {"ok": False, "error": "That action failed. Tell the user it did not complete."},
                    "event": None}

    def _follow(self, args):
        try:
            topic, slug = normalize_topic(args.get("topic", ""))
        except ValueError as e:
            return {"result": {"ok": False, "error": str(e)}, "event": None}
        already = any(s["slug"] == slug for s in self.store.list_subscriptions(self.user_id))
        try:
            self.store.add_subscription(self.user_id, topic, slug, topic, self.s.max_topics_per_user)
        except TopicLimitError:
            return {"result": {"ok": False, "error": f"The user already follows {self.s.max_topics_per_user} "
                               "topics, which is the maximum. Ask them to unfollow one first."}, "event": None}
        result: Dict[str, Any] = {"ok": True, "topic": topic, "already_following": already}
        try:
            r = digest.refresh_topic(self.store, self.llm, self.s,
                                     {"slug": slug, "topic": topic, "query": topic}, fetch=self.fetch)
            result.update(stories_found=r["fetched"], digest_saved=r["digest_saved"],
                          headlines=_compact(r["articles"], 5))
            if not r["fetched"]:
                result["note"] = "No recent stories found yet; it will keep checking."
        except Exception as e:
            print(f"[tools] first refresh failed for {slug}: {e}")
            result["note"] = "Followed, but the first fetch failed. It will be retried on the next scheduled run."
        result["info"] = "Appears in the Following tab and refreshes automatically a few times a day."
        return {"result": result, "event": {"name": "follow_topic", "topic": topic, "slug": slug, "ok": True}}

    def _unfollow(self, args):
        try:
            topic, slug = normalize_topic(args.get("topic", ""))
        except ValueError as e:
            return {"result": {"ok": False, "error": str(e)}, "event": None}
        removed = self.store.remove_subscription(self.user_id, slug)
        if not removed:
            return {"result": {"ok": False, "error": f"The user was not following '{topic}'."}, "event": None}
        return {"result": {"ok": True, "topic": topic, "unfollowed": True},
                "event": {"name": "unfollow_topic", "topic": topic, "slug": slug, "ok": True}}

    def _list(self, _args):
        subs = self.store.list_subscriptions(self.user_id)
        return {"result": {"ok": True, "topics": [s["topic"] for s in subs]}, "event": None}

    def _news(self, args):
        topic = " ".join(str(args.get("topic", "")).split())
        if len(topic) < 2:
            return {"result": {"ok": False, "error": "Need a topic."}, "event": None}
        limit = max(1, min(int(args.get("limit") or 6), 8))
        articles = self.fetch(topic, topic=topic, limit=limit, lang=self.s.news_lang,
                              region=self.s.news_region, max_age_days=self.s.topic_max_age_days)
        return {"result": {"ok": True, "topic": topic, "count": len(articles),
                           "headlines": _compact(articles, limit),
                           "note": "Headlines (with a short summary when the feed provides one). Do not claim details beyond them."}, "event": None}

    def _category(self, args):
        cat = str(args.get("category", "")).lower()
        if cat not in sources.FEEDS_BY_CATEGORY:
            return {"result": {"ok": False, "error": "category must be tech, startups, geopolitics or health."}, "event": None}
        limit = max(1, min(int(args.get("limit") or 6), 8))
        items = _round_robin(self.fetch_category(cat), limit)
        stories = [{"title": a["title"][:140], "source": a.get("source", ""), "summary": a.get("summary", "")[:400],
                    "published": a.get("published", ""), "link": a.get("link", "")} for a in items]
        return {"result": {"ok": True, "category": cat, "count": len(stories), "stories": stories,
                           "note": "Summaries come from the publishers' own feeds."}, "event": None}

    def _read(self, args):
        url = str(args.get("url", "")).strip()
        if not url:
            return {"result": {"ok": False, "error": "Need an article link."}, "event": None}
        try:
            page = self.read(url)
        except reader.ReaderError as e:
            return {"result": {"ok": False, "error": str(e) + " Do not guess the article's details; tell the "
                               "user and point them to the link."}, "event": None}
        return {"result": {"ok": True, "title": page.get("title", ""), "outlet": page.get("host", ""),
                           "text": page["text"],
                           "note": "Excerpt of the article text. Only state what this text supports."},
                "event": None}
