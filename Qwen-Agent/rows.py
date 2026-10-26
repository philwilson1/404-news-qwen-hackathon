"""Maps a scraped article dict to the Supabase `articles` row your frontend already renders.
Only columns that already exist in your `articles` table are written, so no schema change is needed."""
import re
from datetime import datetime, timezone

import verify
from topics import topic_category


def slugify_tag(source: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (source or "").lower()).strip("-") or "general"


def to_article_row(raw: dict, category: str = "", corroboration: dict = None) -> dict:
    """verified is True only when 2+ independent outlets were found reporting the story (see verify.py).
    Without a corroboration result the article is stored as not verified."""
    now_iso = datetime.now(timezone.utc).isoformat()
    corro = corroboration or raw.get("corroboration") or {}
    count = int(corro.get("count", 0))
    status = corro.get("status", "unchecked")
    log = [{"agent": "collector", "status": "completed", "detail": f"Pulled from {raw.get('source')}"}]
    if raw.get("link"):
        log[0]["link"] = raw["link"]  # agent_log is jsonb, so the original link rides along here
    if corro:
        outlets = corro.get("outlets", [])
        if status == "corroborated":
            detail = f"Reported by {count} independent outlets: {', '.join(outlets)}"
        elif status == "single_source":
            detail = "Only one outlet found reporting this so far"
        else:
            detail = "Not cross-checked against other outlets"
        log.append({"agent": "verification", "status": "completed" if status != "unchecked" else "skipped",
                    "detail": detail, "result": status, "count": count, "outlets": outlets})
    return {
        "title": (raw.get("title") or "").strip()[:300],
        "summary": (raw.get("summary") or "").strip()[:600],
        "source": raw.get("source") or "Unknown Source",
        "source_logo": "",
        "author": raw.get("source") or "Staff",
        "vibe": "deep-dives",
        "tag": slugify_tag(raw.get("source", "general")),
        "category": category or raw.get("category", "tech"),
        "verified": status == "corroborated",
        "confidence": verify.score_for(count) if corro else 0.0,
        "image_url": "",
        "views": "0",
        "trending": False,
        "published_at": raw.get("published") or now_iso,
        "read_time": 3,
        "agent_log": log,
        "created_at": now_iso,
    }


def to_topic_row(raw: dict, slug: str) -> dict:
    """Topic stories are headlines pulled from Google News. They count as corroborated only when 2+ outlets in the
    same batch carry the story; otherwise they are stored as not cross-checked."""
    row = to_article_row(raw, category=topic_category(slug))
    row["tag"] = raw.get("topic") or row["tag"]
    return row
