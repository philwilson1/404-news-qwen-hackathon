"""Refresh every followed topic: fetch new stories and write a fresh digest.

Run from the backend folder:   python scripts/refresh_topics.py
Needs: SUPABASE_URL, SUPABASE_SERVICE_KEY, GROQ_API_KEY (SUPABASE_ANON_KEY is not needed).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import digest  # noqa: E402
from config import load_settings  # noqa: E402
from llm import GroqClient  # noqa: E402
from store import SupabaseStore  # noqa: E402


def main() -> int:
    s = load_settings()
    if not (s.supabase_url and s.supabase_service_key):
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY.")
        return 2
    if not s.groq_api_key:
        print("GROQ_API_KEY is not set; digests will fall back to plain headline lists.")
    store = SupabaseStore(s.supabase_url, s.supabase_anon_key, s.supabase_service_key)
    summary = digest.refresh_all(store, GroqClient(s), s)
    print(summary)
    # Fail the workflow only if nothing worked at all.
    return 1 if summary["topics"] and not summary["ok"] else 0


if __name__ == "__main__":
    sys.exit(main())
