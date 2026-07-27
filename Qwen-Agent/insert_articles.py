import os
import re
from datetime import datetime, timezone
from supabase import create_client, Client
from scraper import fetch_articles


def slugify_tag(source: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', source.lower()).strip('-') or "general"


def to_article_row(raw: dict) -> dict:
    """Maps a scraped RSS item into the Supabase `articles` table schema.
    Safe to import from anywhere — has no side effects and needs no env vars."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "title": raw.get("title", "").strip()[:300],
        "summary": raw.get("summary", "").strip()[:600],
        "source": raw.get("source", "Unknown Source"),
        "source_logo": "",
        "author": raw.get("source", "Staff"),
        "vibe": "deep-dives",
        "tag": slugify_tag(raw.get("source", "general")),
        "verified": True,
        "confidence": 0.8,
        "image_url": "",
        "views": "0",
        "trending": False,
        "published_at": raw.get("published") or now_iso,
        "read_time": 3,
        "agent_log": [
            {"agent": "scraper", "status": "completed", "detail": f"Pulled from {raw.get('source')}"},
        ],
        "created_at": now_iso,
    }


def get_existing_titles(client: Client) -> set:
    try:
        res = client.table("articles").select("title").execute()
        return {row["title"] for row in (res.data or [])}
    except Exception as e:
        print(f"[warn] Could not fetch existing titles: {e}")
        return set()


def main():
    """CLI entry point — only runs when this file is executed directly,
    e.g. `python insert_articles.py`. Not triggered by importing this module."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_service_key:
        raise SystemExit(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables.\n"
            "Set them in your terminal first, then re-run this script."
        )

    supabase: Client = create_client(supabase_url, supabase_service_key)

    print("Fetching real articles from RSS sources...")
    raw_articles = fetch_articles(force=True)
    print(f"Fetched {len(raw_articles)} raw articles.")

    if not raw_articles:
        print("No articles fetched — check your internet connection or RSS feed URLs in scraper.py.")
        return

    existing_titles = get_existing_titles(supabase)
    new_rows = [
        to_article_row(a) for a in raw_articles
        if a.get("title") and a["title"].strip() not in existing_titles
    ]

    if not new_rows:
        print("No new articles to insert — everything already exists in the table.")
        return

    print(f"Inserting {len(new_rows)} new articles into Supabase...")
    try:
        result = supabase.table("articles").insert(new_rows).execute()
        print(f"Success! Inserted {len(result.data)} articles.")
    except Exception as e:
        print(f"[error] Insert failed: {e}")


if __name__ == "__main__":
    main()