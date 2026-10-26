"""404 News backend (Groq edition).

Start command on Render is unchanged:  gunicorn app:app --workers 1 --threads 8 --timeout 120
"""
import json
import threading
import traceback

from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import agent
import digest
import sources
from config import Settings, load_settings
from llm import GroqClient, LLMError
import verify
from rows import to_article_row
from store import Store, SupabaseStore


def create_app(settings: Settings = None, store: Store = None, llm: GroqClient = None) -> Flask:
    s = settings or load_settings()
    app = Flask(__name__)
    CORS(app, origins=s.allowed_origins, supports_credentials=True)
    limiter = Limiter(get_remote_address, app=app, default_limits=[], storage_uri="memory://")

    if store is None and s.supabase_url and s.supabase_service_key:
        store = SupabaseStore(s.supabase_url, s.supabase_anon_key, s.supabase_service_key)
    llm = llm or GroqClient(s)
    batch_lock = threading.Lock()

    # ---- helpers --------------------------------------------------------
    def verified_user_id():
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer ") or store is None:
            return None
        return store.get_user_id(header.split(" ", 1)[1])

    def has_pipeline_secret() -> bool:
        return bool(s.pipeline_secret) and request.headers.get("X-Pipeline-Secret", "") == s.pipeline_secret

    def sse(obj) -> str:
        return f"data: {json.dumps(obj)}\n\n"

    # ---- routes ---------------------------------------------------------
    @app.get("/health")
    def health():
        return jsonify({"ok": True, "groq_configured": bool(s.groq_api_key), "model": s.model,
                        "database_configured": store is not None})

    @app.route("/chat", methods=["POST", "OPTIONS"])
    @limiter.limit("30 per hour")
    def chat():
        if request.method == "OPTIONS":
            return "", 200
        user_id = verified_user_id()
        if not user_id:
            return jsonify({"error": "Unauthorized. Please sign in."}), 401
        data = request.get_json(silent=True) or {}
        history = data.get("messages") or ([{"role": "user", "content": data["message"]}] if data.get("message") else [])
        if not history:
            return jsonify({"error": "No messages found in request"}), 400
        articles = data.get("articles") or []

        @stream_with_context
        def generate():
            try:
                for ev in agent.run_agent(llm, store, s, user_id, history, articles):
                    if ev["type"] == "text":
                        yield sse({"choices": [{"delta": {"content": ev["text"]}}]})
                    else:
                        yield sse({"event": "tool", **{k: v for k, v in ev.items() if k != "type"}})
            except LLMError as e:
                print(f"[chat] LLM error: {e}")
                yield sse({"choices": [{"delta": {"content": f"\n\n{e.public_message}"}}]})
            except Exception as e:
                traceback.print_exc()
                yield sse({"choices": [{"delta": {"content": "\n\nSomething went wrong on the server. Please try again."}}]})
            yield "data: [DONE]\n\n"

        resp = Response(generate(), mimetype="text/event-stream")
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["X-Accel-Buffering"] = "no"
        return resp

    @app.route("/topics/refresh", methods=["POST", "OPTIONS"])
    @limiter.limit("20 per hour")
    def refresh_one_topic():
        """Fetch fresh stories + a new digest for one topic the signed-in user follows."""
        if request.method == "OPTIONS":
            return "", 200
        user_id = verified_user_id()
        if not user_id:
            return jsonify({"error": "Unauthorized. Please sign in."}), 401
        slug = ((request.get_json(silent=True) or {}).get("slug") or "").strip()
        mine = {t["slug"]: t for t in store.list_subscriptions(user_id)}
        if slug not in mine:
            return jsonify({"error": "You are not following that topic."}), 404
        t = mine[slug]
        try:
            r = digest.refresh_topic(store, llm, s, {"slug": slug, "topic": t["topic"], "query": t.get("query") or t["topic"]})
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": "Could not refresh that topic right now."}), 502
        return jsonify({"slug": slug, "fetched": r["fetched"], "new": r["new"], "digest_saved": r["digest_saved"]})

    @app.route("/run-digests", methods=["POST", "OPTIONS"])
    def run_digests():
        """Cron entry point. Returns immediately and works in the background so the host's
        request timeout is never hit. Prefer scripts/refresh_topics.py from GitHub Actions."""
        if request.method == "OPTIONS":
            return "", 200
        if not has_pipeline_secret():
            return jsonify({"error": "Unauthorized."}), 401
        if store is None:
            return jsonify({"error": "Database not configured."}), 500
        if not batch_lock.acquire(blocking=False):
            return jsonify({"status": "already running"}), 202

        def work():
            try:
                print("[run-digests]", digest.refresh_all(store, llm, s))
            finally:
                batch_lock.release()

        threading.Thread(target=work, daemon=True).start()
        return jsonify({"status": "started"}), 202

    @app.route("/run-pipeline", methods=["POST", "OPTIONS"])
    @limiter.limit("10 per hour")
    def run_pipeline():
        """Original category pipeline (tech / geopolitics / startups), kept as is."""
        if request.method == "OPTIONS":
            return "", 200
        if not (verified_user_id() or has_pipeline_secret()):
            return jsonify({"error": "Unauthorized. Please sign in."}), 401
        if store is None:
            return jsonify({"error": "Pipeline not configured on the server."}), 500
        try:
            raw = sources.fetch_articles(category="all", force=True)
            if not raw:
                return jsonify({"inserted": 0, "message": "No articles fetched from sources."}), 200
            fresh = []
            for cat in {a["category"] for a in raw}:
                batch = [a for a in raw if a["category"] == cat and a.get("title")]
                seen = store.existing_titles([a["title"].strip() for a in batch], cat)
                fresh += [a for a in batch if a["title"].strip() not in seen]
            verify.annotate(fresh, pool=raw)  # counts independent outlets per story (bounded by a time budget)
            inserted = store.insert_articles([to_article_row(a) for a in fresh])
            msg = f"Inserted {inserted} new articles." if inserted else "No new articles. Everything already exists."
            return jsonify({"inserted": inserted, "message": msg}), 200
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    return app


app = create_app()

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
