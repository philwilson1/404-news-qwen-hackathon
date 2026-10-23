"""Persistence. `Store` is the interface the rest of the code uses.
SupabaseStore talks to your real database; MemoryStore is for tests and local dev."""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set


class TopicLimitError(Exception):
    pass


class Store:
    def get_user_id(self, token: str) -> Optional[str]: raise NotImplementedError
    def list_subscriptions(self, user_id: str) -> List[dict]: raise NotImplementedError
    def add_subscription(self, user_id: str, topic: str, slug: str, query: str, limit: int) -> dict: raise NotImplementedError
    def remove_subscription(self, user_id: str, slug: str) -> bool: raise NotImplementedError
    def distinct_topics(self) -> List[dict]: raise NotImplementedError
    def touch_topic(self, slug: str) -> None: raise NotImplementedError
    def existing_titles(self, titles: List[str], category: str) -> Set[str]: raise NotImplementedError
    def insert_articles(self, rows: List[dict]) -> int: raise NotImplementedError
    def latest_digest(self, slug: str) -> Optional[dict]: raise NotImplementedError
    def save_digest(self, slug: str, topic: str, content: str, headlines: List[dict], model: str) -> None: raise NotImplementedError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore(Store):
    def __init__(self, tokens: Optional[Dict[str, str]] = None):
        self.tokens = tokens or {}
        self.subs: List[dict] = []
        self.articles: List[dict] = []
        self.digests: List[dict] = []

    def get_user_id(self, token):
        return self.tokens.get(token)

    def list_subscriptions(self, user_id):
        return [dict(s) for s in self.subs if s["user_id"] == user_id]

    def add_subscription(self, user_id, topic, slug, query, limit):
        for s in self.subs:
            if s["user_id"] == user_id and s["slug"] == slug:
                return dict(s)
        if len(self.list_subscriptions(user_id)) >= limit:
            raise TopicLimitError()
        row = {"user_id": user_id, "topic": topic, "slug": slug, "query": query,
               "created_at": _now(), "last_refreshed_at": None}
        self.subs.append(row)
        return dict(row)

    def remove_subscription(self, user_id, slug):
        before = len(self.subs)
        self.subs = [s for s in self.subs if not (s["user_id"] == user_id and s["slug"] == slug)]
        return len(self.subs) < before

    def distinct_topics(self):
        seen: Dict[str, dict] = {}
        for s in self.subs:
            seen.setdefault(s["slug"], {"slug": s["slug"], "topic": s["topic"], "query": s["query"]})
        return list(seen.values())

    def touch_topic(self, slug):
        for s in self.subs:
            if s["slug"] == slug:
                s["last_refreshed_at"] = _now()

    def existing_titles(self, titles, category):
        return {a["title"] for a in self.articles if a["category"] == category and a["title"] in set(titles)}

    def insert_articles(self, rows):
        self.articles.extend(rows)
        return len(rows)

    def latest_digest(self, slug):
        mine = [d for d in self.digests if d["slug"] == slug]
        return mine[-1] if mine else None

    def save_digest(self, slug, topic, content, headlines, model):
        self.digests.append({"slug": slug, "topic": topic, "content": content,
                             "headlines": headlines, "model": model, "created_at": _now()})


class SupabaseStore(Store):
    def __init__(self, url: str, anon_key: str, service_key: str):
        from supabase import create_client  # imported here so tests do not need the package

        self.auth = create_client(url, anon_key) if url and anon_key else None
        self.db = create_client(url, service_key) if url and service_key else None

    @property
    def configured(self) -> bool:
        return self.db is not None

    def get_user_id(self, token):
        if not self.auth:
            return None
        try:
            res = self.auth.auth.get_user(token)
            return res.user.id if res and res.user else None
        except Exception:
            return None

    def list_subscriptions(self, user_id):
        res = self.db.table("topic_subscriptions").select("*").eq("user_id", user_id) \
            .order("created_at").execute()
        return res.data or []

    def add_subscription(self, user_id, topic, slug, query, limit):
        existing = self.list_subscriptions(user_id)
        for s in existing:
            if s["slug"] == slug:
                return s
        if len(existing) >= limit:
            raise TopicLimitError()
        res = self.db.table("topic_subscriptions").insert(
            {"user_id": user_id, "topic": topic, "slug": slug, "query": query}).execute()
        return (res.data or [{}])[0]

    def remove_subscription(self, user_id, slug):
        res = self.db.table("topic_subscriptions").delete().eq("user_id", user_id).eq("slug", slug).execute()
        return bool(res.data)

    def distinct_topics(self):
        res = self.db.table("topic_subscriptions").select("slug,topic,query").execute()
        seen: Dict[str, dict] = {}
        for r in res.data or []:
            seen.setdefault(r["slug"], r)
        return list(seen.values())

    def touch_topic(self, slug):
        self.db.table("topic_subscriptions").update({"last_refreshed_at": _now()}).eq("slug", slug).execute()

    def existing_titles(self, titles, category):
        found: Set[str] = set()
        titles = list(titles)
        for i in range(0, len(titles), 50):  # keep the request URL short
            chunk = titles[i:i + 50]
            res = self.db.table("articles").select("title").eq("category", category).in_("title", chunk).execute()
            found.update(r["title"] for r in (res.data or []))
        return found

    def insert_articles(self, rows):
        if not rows:
            return 0
        res = self.db.table("articles").insert(rows).execute()
        return len(res.data or [])

    def latest_digest(self, slug):
        res = self.db.table("topic_digests").select("*").eq("slug", slug) \
            .order("created_at", desc=True).limit(1).execute()
        return (res.data or [None])[0]

    def save_digest(self, slug, topic, content, headlines, model):
        self.db.table("topic_digests").insert({
            "slug": slug, "topic": topic, "content": content, "headlines": headlines,
            "article_count": len(headlines), "model": model}).execute()
