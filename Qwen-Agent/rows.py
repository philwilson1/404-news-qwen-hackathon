"""Maps a scraped article dict to the Supabase `articles` row your frontend already renders.
Only columns that already exist in your `articles` table are written, so no schema change is needed."""
import re
from datetime import datetime, timezone

from topics import topic_category


def slugify_tag(source: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (source or "").lower()).strip("-") or "general"


def to_article_row(raw: dict, category: str = "", verified: bool = True, confidence: float = 0.8) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    log = {"agent": "collector", "status": "completed", "detail": f"Pulled from {raw.get('source')}"}
    if raw.get("link"):
        log["link"] = raw["link"]  # agent_log is jsonb, so the original link rides along here
    return {
        "title": (raw.get("title") or "").strip()[:300],
        "summary": (raw.get("summary") or "").strip()[:600],
        "source": raw.get("source") or "Unknown Source",
        "source_logo": "",
        "author": raw.get("source") or "Staff",
        "vibe": "deep-dives",
        "tag": slugify_tag(raw.get("source", "general")),
        "category": category or raw.get("category", "tech"),
        "verified": verified,
        "confidence": confidence,
        "image_url": "",
        "views": "0",
        "trending": False,
        "published_at": raw.get("published") or now_iso,
        "read_time": 3,
        "agent_log": [log],
        "created_at": now_iso,
    }


def to_topic_row(raw: dict, slug: str) -> dict:
    """Topic stories are headlines pulled from Google News. They are not cross-checked,
    so they are stored as unverified rather than claiming a verification that did not happen."""
    row = to_article_row(raw, category=topic_category(slug), verified=False, confidence=0.0)
    row["tag"] = raw.get("topic") or row["tag"]
    return row
