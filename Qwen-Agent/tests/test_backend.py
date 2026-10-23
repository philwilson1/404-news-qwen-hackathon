"""Run with:  python -m unittest discover -s tests -v   (from the backend folder)
No network, no API keys. Groq's HTTP layer, the news feeds and the database are all faked."""
import json
import os
import sys
import time
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# flask-cors and flask-limiter are only needed for real deployments; stub them if absent.
try:
    import flask_cors  # noqa: F401
    import flask_limiter  # noqa: F401
except ImportError:
    fc = types.ModuleType("flask_cors"); fc.CORS = lambda *a, **k: None
    fl = types.ModuleType("flask_limiter")
    class _Limiter:
        def __init__(self, *a, **k): pass
        def limit(self, _s): return lambda f: f
    fl.Limiter = _Limiter
    flu = types.ModuleType("flask_limiter.util"); flu.get_remote_address = lambda: "test"
    sys.modules.update({"flask_cors": fc, "flask_limiter": fl, "flask_limiter.util": flu})

import agent  # noqa: E402
import digest  # noqa: E402
import sources  # noqa: E402
from config import Settings  # noqa: E402
from llm import GroqClient, LLMError  # noqa: E402
from store import MemoryStore  # noqa: E402
from tools import ToolRunner  # noqa: E402
from topics import normalize_topic, slugify  # noqa: E402


# ----------------------------------------------------------------------------- fakes
class FakeResp:
    def __init__(self, status=200, body=None, headers=None, lines=None):
        self.status_code, self._body, self.headers, self._lines = status, body or {}, headers or {}, lines or []
        self.text = json.dumps(self._body)
        self.closed = False
    def json(self): return self._body
    def iter_lines(self, decode_unicode=False):
        # Real requests: a text/event-stream response with no charset is decoded as ISO-8859-1 when
        # decode_unicode=True, which turns UTF-8 punctuation into mojibake. Mimic that.
        raw = [l.encode("utf-8") for l in self._lines]
        return iter([b.decode("latin-1") for b in raw] if decode_unicode else raw)
    def close(self): self.closed = True


class FakeSession:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def post(self, url, json=None, headers=None, timeout=None, stream=False):
        self.calls.append(json)
        return self.responses.pop(0)


def ok_body(text="hi"):
    return {"choices": [{"message": {"content": text}}]}


def err(status, msg="", code="", retry=None):
    return FakeResp(status, {"error": {"message": msg, "code": code}},
                    {"retry-after": str(retry)} if retry is not None else {})


def make_client(responses, **kw):
    sleeps = []
    s = Settings(groq_api_key="k", rpm=600, **kw)
    return GroqClient(s, session=FakeSession(responses), sleep=sleeps.append), sleeps


def sse_lines(*chunks):
    return [f"data: {json.dumps(c, ensure_ascii=False)}" for c in chunks] + ["data: [DONE]"]


class ScriptedLLM:
    """Stands in for GroqClient inside the agent: each stream_chat call plays the next script."""
    def __init__(self, scripts, complete_text="DIGEST TEXT"):
        self.scripts, self.seen, self.complete_text = list(scripts), [], complete_text
    def stream_chat(self, messages, tools=None, **kw):
        self.seen.append({"messages": [dict(m) for m in messages], "tools": tools})
        script = self.scripts.pop(0)
        if isinstance(script, Exception):
            raise script
        text, calls = script
        if text:
            yield {"type": "text", "text": text}
        yield {"type": "done", "content": text, "tool_calls": calls, "model": "fake"}
    def complete(self, messages, **kw):
        return {"content": self.complete_text, "tool_calls": [], "model": "fake-fast"}


def tool_call(name, args, id="c1"):
    return {"id": id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def fake_articles(n=3, prefix="Quantum"):
    return [{"title": f"{prefix} story {i}", "summary": "", "source": f"Outlet{i}", "link": f"https://x/{i}",
             "published": "Fri, 23 Oct 2026 10:00:00 GMT", "category": "topic", "topic": prefix} for i in range(n)]


# ----------------------------------------------------------------------------- topics
class TopicTests(unittest.TestCase):
    def test_slug_and_validation(self):
        self.assertEqual(normalize_topic("  Quantum   Computing! "), ("Quantum Computing!", "quantum-computing"))
        self.assertEqual(slugify("Café Économie"), "cafe-economie")
        for bad in ["", "a", "!!!", "x" * 61]:
            with self.assertRaises(ValueError):
                normalize_topic(bad)


# ----------------------------------------------------------------------------- sources
class SourceTests(unittest.TestCase):
    def test_google_news_url(self):
        u = sources.google_news_url("quantum computing", "en", "NG", 7)
        self.assertIn("q=quantum+computing+when%3A7d", u)
        self.assertIn("gl=NG", u)
        self.assertIn("ceid=NG:en", u)

    def test_entry_mapping_strips_outlet_suffix(self):
        now = time.gmtime()
        e = {"title": "Chip breakthrough announced - Reuters", "source": {"title": "Reuters"},
             "link": "https://n/1", "summary": "<a>Chip breakthrough announced</a> Reuters", "published_parsed": now}
        a = sources.entry_to_topic_article(e, "chips")
        self.assertEqual(a["title"], "Chip breakthrough announced")
        self.assertEqual(a["source"], "Reuters")
        self.assertEqual(a["summary"], "")  # Google's description only repeats the headline
        self.assertIsNone(sources.entry_to_topic_article({"title": ""}, "x"))

    def test_entry_without_source_field_splits_title(self):
        a = sources.entry_to_topic_article({"title": "Big news - BBC News"}, "x")
        self.assertEqual((a["title"], a["source"]), ("Big news", "BBC News"))

    def test_select_dedupes_drops_stale_and_mixes_outlets(self):
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        def art(t, src, days):
            return {"title": t, "source": src, "published_dt": now - timedelta(days=days)}
        items = [art("A one", "S1", 0.1), art("A one", "S2", 0.1),   # duplicate headline
                 art("Old", "S1", 30),                               # too old
                 art("B", "S1", 0.2), art("C", "S1", 0.3), art("D", "S1", 0.4), art("E", "S2", 0.5)]
        out = sources.select_articles(items, limit=4, max_age_days=7, per_source=2)
        titles = [a["title"] for a in out]
        self.assertNotIn("Old", titles)
        self.assertEqual(titles.count("A one"), 1)
        self.assertEqual(len(out), 4)
        self.assertIn("E", titles)  # S2 gets a slot even though S1 has newer stories


# ----------------------------------------------------------------------------- llm
class LLMTests(unittest.TestCase):
    def test_complete_ok_and_reasoning_param(self):
        c, _ = make_client([FakeResp(200, ok_body("hello"))])
        out = c.complete([{"role": "user", "content": "x"}])
        self.assertEqual(out["content"], "hello")
        sent = c.session.calls[0]
        self.assertEqual(sent["model"], "openai/gpt-oss-20b")
        self.assertEqual(sent["reasoning_effort"], "low")

    def test_short_429_retries_same_model(self):
        c, sleeps = make_client([err(429, "slow down", retry=2), FakeResp(200, ok_body("ok"))])
        self.assertEqual(c.complete([])["content"], "ok")
        self.assertIn(2.0, sleeps)
        self.assertEqual(c.session.calls[0]["model"], c.session.calls[1]["model"])

    def test_daily_limit_falls_back_to_other_model(self):
        c, _ = make_client([err(429, "Rate limit reached ... tokens per day (TPD)", retry=3000),
                            FakeResp(200, ok_body("from fallback"))], fast_model="a/one", fallback_models=["b/two"])
        out = c.complete([])
        self.assertEqual(out["model"], "b/two")

    def test_decommissioned_model_falls_back(self):
        c, _ = make_client([err(400, "The model has been decommissioned", code="model_decommissioned"),
                            FakeResp(200, ok_body("ok"))], fast_model="old/model", fallback_models=["new/model"])
        self.assertEqual(c.complete([])["model"], "new/model")

    def test_404_model_not_found_falls_back(self):
        c, _ = make_client([err(404, "The model `x` does not exist"),
                            FakeResp(200, ok_body("ok"))], fast_model="gone/model", fallback_models=["new/model"])
        self.assertEqual(c.complete([])["model"], "new/model")

    def test_unsupported_reasoning_param_is_dropped(self):
        c, _ = make_client([err(400, "property 'reasoning_effort' is unsupported"), FakeResp(200, ok_body("ok"))])
        self.assertEqual(c.complete([])["content"], "ok")
        self.assertNotIn("reasoning_effort", c.session.calls[1])

    def test_bad_key_raises_with_friendly_message(self):
        c, _ = make_client([err(401, "Invalid API Key")])
        with self.assertRaises(LLMError) as cm:
            c.complete([])
        self.assertIn("GROQ_API_KEY", cm.exception.public_message)

    def test_missing_key(self):
        c = GroqClient(Settings(groq_api_key=""), session=FakeSession([]))
        with self.assertRaises(LLMError):
            c.complete([])

    def test_all_models_limited_raises_429(self):
        c, _ = make_client([err(429, "tokens per day (TPD)", retry=900)] * 5,
                           fast_model="a", fallback_models=["b"], model="c")
        with self.assertRaises(LLMError) as cm:
            c.complete([])
        self.assertEqual(cm.exception.status, 429)

    def test_stream_text_and_fragmented_tool_call(self):
        lines = sse_lines(
            {"choices": [{"delta": {"content": "Sure. "}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "t1", "function": {"name": "follow_topic", "arguments": ""}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"topic": "AI'}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ' chips"}'}}]}}]},
        )
        c, _ = make_client([FakeResp(200, lines=lines)])
        events = list(c.stream_chat([{"role": "user", "content": "x"}], tools=[{"type": "function"}]))
        self.assertEqual(events[0], {"type": "text", "text": "Sure. "})
        done = events[-1]
        self.assertEqual(done["tool_calls"][0]["function"]["name"], "follow_topic")
        self.assertEqual(json.loads(done["tool_calls"][0]["function"]["arguments"]), {"topic": "AI chips"})
        self.assertEqual(c.session.calls[0]["tool_choice"], "auto")

    def test_stream_keeps_non_ascii_text_intact(self):
        text = "AI\u2011discovered bug \u2014 Nigeria\u2019s bill"
        c, _ = make_client([FakeResp(200, lines=sse_lines({"choices": [{"delta": {"content": text}}]}))])
        events = list(c.stream_chat([{"role": "user", "content": "x"}]))
        self.assertEqual(events[0]["text"], text)

    def test_throttle_spaces_requests(self):
        sleeps, t = [], [0.0]
        s = Settings(groq_api_key="k", rpm=30)  # one request per 2 seconds
        c = GroqClient(s, session=FakeSession([FakeResp(200, ok_body())] * 2),
                       sleep=lambda x: (sleeps.append(x), t.__setitem__(0, t[0] + x)), clock=lambda: t[0])
        c.complete([]); c.complete([])
        self.assertTrue(any(abs(x - 2.0) < 1e-6 for x in sleeps))


# ----------------------------------------------------------------------------- digest
class DigestTests(unittest.TestCase):
    def setUp(self):
        self.s = Settings(groq_api_key="k")
        self.store = MemoryStore()
        self.topic = {"slug": "quantum", "topic": "Quantum", "query": "Quantum"}

    def test_first_run_stores_articles_and_digest_second_run_is_quiet(self):
        arts = fake_articles(3)
        llm = ScriptedLLM([])
        r1 = digest.refresh_topic(self.store, llm, self.s, self.topic, fetch=lambda *a, **k: arts)
        self.assertEqual((r1["new"], r1["digest_saved"]), (3, True))
        self.assertEqual(self.store.articles[0]["category"], "topic-quantum")
        self.assertFalse(self.store.articles[0]["verified"])
        self.assertEqual(self.store.latest_digest("quantum")["content"], "DIGEST TEXT")
        r2 = digest.refresh_topic(self.store, llm, self.s, self.topic, fetch=lambda *a, **k: arts)
        self.assertEqual((r2["new"], r2["digest_saved"]), (0, False))
        self.assertEqual(len(self.store.digests), 1)

    def test_new_story_triggers_new_digest_with_only_new_story(self):
        digest.refresh_topic(self.store, ScriptedLLM([]), self.s, self.topic, fetch=lambda *a, **k: fake_articles(2))
        r = digest.refresh_topic(self.store, ScriptedLLM([]), self.s, self.topic, fetch=lambda *a, **k: fake_articles(3))
        self.assertEqual(r["new"], 1)
        self.assertEqual(len(self.store.digests[-1]["headlines"]), 1)

    def test_groq_down_falls_back_to_headline_list(self):
        class Down:
            def complete(self, *a, **k): raise LLMError("down", status=429)
        digest.refresh_topic(self.store, Down(), self.s, self.topic, fetch=lambda *a, **k: fake_articles(2))
        d = self.store.latest_digest("quantum")
        self.assertEqual(d["model"], "headlines-only")
        self.assertIn("Quantum story 0", d["content"])

    def test_refresh_all_survives_one_broken_topic(self):
        self.store.add_subscription("u", "Good", "good", "Good", 10)
        self.store.add_subscription("u", "Bad", "bad", "Bad", 10)
        orig = sources.fetch_topic_articles
        def fetch(query, **k):
            if query == "Bad":
                raise RuntimeError("feed down")
            return fake_articles(1, prefix="Good")
        sources.fetch_topic_articles = fetch
        try:
            summary = digest.refresh_all(self.store, ScriptedLLM([]), Settings(digest_pause_s=0), sleep=lambda x: None)
        finally:
            sources.fetch_topic_articles = orig
        self.assertEqual((summary["ok"], summary["failed"]), (1, 1))


# ----------------------------------------------------------------------------- agent + tools
class AgentTests(unittest.TestCase):
    def setUp(self):
        self.s = Settings(groq_api_key="k", digest_pause_s=0)
        self.store = MemoryStore({"tok": "user1"})

    def runner(self, llm):
        return ToolRunner(self.store, llm, self.s, "user1", fetch=lambda *a, **k: fake_articles(3, "AI chips"))

    def test_follow_flow(self):
        llm = ScriptedLLM([("", [tool_call("follow_topic", {"topic": "AI chips"})]),
                           ("You're now following AI chips.", [])])
        events = list(agent.run_agent(llm, self.store, self.s, "user1",
                                      [{"role": "user", "content": "keep me in the loop on AI chips"}],
                                      runner=self.runner(llm)))
        subs = self.store.list_subscriptions("user1")
        self.assertEqual([x["slug"] for x in subs], ["ai-chips"])
        self.assertEqual(len(self.store.articles), 3)
        self.assertEqual(len(self.store.digests), 1)
        done = [e for e in events if e["type"] == "tool" and e["status"] == "done"][0]
        self.assertTrue(done["ok"] and done["changed"])
        self.assertEqual(done["topic"], "AI chips")
        # the model saw the tool result before writing its final answer
        tool_msg = [m for m in llm.seen[1]["messages"] if m["role"] == "tool"][0]
        self.assertIn("AI chips story 0", tool_msg["content"])
        self.assertEqual("".join(e["text"] for e in events if e["type"] == "text"), "You're now following AI chips.")

    def test_followed_topics_are_in_system_prompt_and_history_trimmed(self):
        self.store.add_subscription("user1", "Cybersecurity", "cybersecurity", "Cybersecurity", 10)
        hist = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(20)]
        llm = ScriptedLLM([("ok", [])])
        list(agent.run_agent(llm, self.store, self.s, "user1", hist, runner=self.runner(llm)))
        msgs = llm.seen[0]["messages"]
        self.assertIn("Cybersecurity", msgs[0]["content"])
        self.assertEqual(len(msgs), 1 + agent.HISTORY_MESSAGES)

    def test_topic_limit_reported_to_model(self):
        s = Settings(groq_api_key="k", max_topics_per_user=1)
        self.store.add_subscription("user1", "One", "one", "One", 1)
        r = ToolRunner(self.store, ScriptedLLM([]), s, "user1", fetch=lambda *a, **k: [])
        out = r.run("follow_topic", json.dumps({"topic": "Two"}))
        self.assertFalse(out["result"]["ok"])
        self.assertIsNone(out["event"])

    def test_unfollow_and_bad_args(self):
        r = self.runner(ScriptedLLM([]))
        r.run("follow_topic", json.dumps({"topic": "Space"}))
        self.assertTrue(r.run("unfollow_topic", json.dumps({"topic": "space"}))["result"]["ok"])
        self.assertFalse(r.run("unfollow_topic", json.dumps({"topic": "space"}))["result"]["ok"])
        self.assertFalse(r.run("follow_topic", "{not json")["result"]["ok"])
        self.assertFalse(r.run("nope", "{}")["result"]["ok"])

    def test_category_tool_returns_summaries_mixed_across_outlets(self):
        items = [{"title": f"A{i}", "source": "TechCrunch", "summary": "s" * 500, "link": f"https://a/{i}"} for i in range(5)]
        items += [{"title": "B0", "source": "Ars", "summary": "short", "link": "https://b/0"}]
        r = ToolRunner(self.store, ScriptedLLM([]), self.s, "user1", fetch_category=lambda cat: list(items))
        out = r.run("get_category_news", json.dumps({"category": "tech", "limit": 3}))["result"]
        self.assertTrue(out["ok"])
        self.assertEqual([x["source"] for x in out["stories"]][:2], ["TechCrunch", "Ars"])
        self.assertLessEqual(len(out["stories"][0]["summary"]), 240)
        self.assertFalse(r.run("get_category_news", json.dumps({"category": "sports"}))["result"]["ok"])

    def test_news_tool_does_not_follow(self):
        r = self.runner(ScriptedLLM([]))
        out = r.run("get_topic_news", json.dumps({"topic": "Lagos traffic", "limit": 2}))
        self.assertEqual(len(out["result"]["headlines"]), 2)
        self.assertEqual(self.store.list_subscriptions("user1"), [])

    def test_malformed_tool_call_falls_back_to_plain_answer(self):
        llm = ScriptedLLM([LLMError("bad tool call", status=400, code="tool_use_failed"), ("Use the Following tab.", [])])
        events = list(agent.run_agent(llm, self.store, self.s, "user1",
                                      [{"role": "user", "content": "follow x"}], runner=self.runner(llm)))
        self.assertIsNone(llm.seen[1]["tools"])
        self.assertEqual(events[0]["text"], "Use the Following tab.")

    def test_tool_loop_is_bounded(self):
        looping = [("", [tool_call("list_followed_topics", {}, id=f"c{i}")]) for i in range(10)]
        llm = ScriptedLLM(looping)
        list(agent.run_agent(llm, self.store, self.s, "user1", [{"role": "user", "content": "x"}], runner=self.runner(llm)))
        self.assertEqual(len(llm.seen), agent.MAX_TOOL_ROUNDS + 1)
        self.assertIsNone(llm.seen[-1]["tools"])


# ----------------------------------------------------------------------------- HTTP routes
class RouteTests(unittest.TestCase):
    def setUp(self):
        import app as appmod
        self.s = Settings(groq_api_key="k", pipeline_secret="sekret", digest_pause_s=0)
        self.store = MemoryStore({"tok": "user1"})
        self.llm = ScriptedLLM([("", [tool_call("follow_topic", {"topic": "Space"})]), ("Following Space.", [])])
        self.orig = sources.fetch_topic_articles
        sources.fetch_topic_articles = lambda *a, **k: fake_articles(2, "Space")
        self.client = appmod.create_app(self.s, self.store, self.llm).test_client()

    def tearDown(self):
        sources.fetch_topic_articles = self.orig

    def test_chat_requires_login(self):
        self.assertEqual(self.client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]}).status_code, 401)

    def test_chat_streams_text_and_tool_events(self):
        r = self.client.post("/chat", json={"messages": [{"role": "user", "content": "follow space"}]},
                             headers={"Authorization": "Bearer tok"})
        self.assertEqual(r.status_code, 200)
        body = r.get_data(as_text=True)
        self.assertIn('"event": "tool"', body)
        self.assertIn('"changed": true', body)
        self.assertIn("Following Space.", body)
        self.assertTrue(body.rstrip().endswith("data: [DONE]"))
        self.assertEqual(self.store.list_subscriptions("user1")[0]["slug"], "space")

    def test_chat_surfaces_friendly_llm_error(self):
        self.llm.scripts = [LLMError("x", status=429)]
        r = self.client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]},
                             headers={"Authorization": "Bearer tok"})
        self.assertIn("free-tier limit", r.get_data(as_text=True))

    def test_refresh_only_own_topics(self):
        h = {"Authorization": "Bearer tok"}
        self.assertEqual(self.client.post("/topics/refresh", json={"slug": "space"}, headers=h).status_code, 404)
        self.store.add_subscription("user1", "Space", "space", "Space", 10)
        r = self.client.post("/topics/refresh", json={"slug": "space"}, headers=h)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["new"], 2)

    def test_run_digests_needs_secret(self):
        self.assertEqual(self.client.post("/run-digests").status_code, 401)
        self.store.add_subscription("user1", "Space", "space", "Space", 10)
        r = self.client.post("/run-digests", headers={"X-Pipeline-Secret": "sekret"})
        self.assertEqual(r.status_code, 202)

    def test_health(self):
        self.assertTrue(self.client.get("/health").get_json()["groq_configured"])


if __name__ == "__main__":
    unittest.main()
