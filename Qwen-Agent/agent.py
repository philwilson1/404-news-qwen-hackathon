"""The chat agent: streams Groq output and runs tool calls (follow a topic, fetch news...)."""
import json
from datetime import date
from typing import Dict, Iterator, List, Optional

from config import Settings
from llm import GroqClient, LLMError
from store import Store
from tools import TOOL_SCHEMAS, ToolRunner

MAX_TOOL_ROUNDS = 3
MAX_CALLS_PER_ROUND = 3
HISTORY_MESSAGES = 8
HISTORY_CHARS = 1500


def system_prompt(followed: List[str]) -> str:
    topics = ", ".join(followed) if followed else "none yet"
    return (
        "You are 404 AI, the news assistant inside the 404 News app. "
        f"Today is {date.today().isoformat()}. No emoji. Use short markdown: plain text, bold, bullets.\n"
        f"Topics this user follows: {topics}.\n"
        "Rules:\n"
        "- If the user asks to follow, track, watch, or be kept in the loop or updated on something, call "
        "follow_topic. Only say you are following a topic after the tool returned ok=true.\n"
        "- For anything that depends on recent events, call get_topic_news instead of relying on memory.\n"
        "- You only see headlines, not full articles. Never invent details; say what is unknown.\n"
        "- Cite outlets by name and include the link when you quote a headline.\n"
        "- Keep answers brief. After following a topic, confirm it in one or two lines and show the top headlines."
    )


def build_messages(history: List[dict], followed: List[str], articles: List[dict]) -> List[dict]:
    msgs: List[dict] = [{"role": "system", "content": system_prompt(followed)}]
    trimmed = [m for m in history if m.get("role") in ("user", "assistant") and m.get("content")]
    trimmed = trimmed[-HISTORY_MESSAGES:]
    for i, m in enumerate(trimmed):
        content = str(m["content"])[:HISTORY_CHARS]
        if articles and i == len(trimmed) - 1 and m["role"] == "user":
            ctx = "\n".join(f"- {a.get('title', '')} ({a.get('source', '')}): {str(a.get('summary', ''))[:240]}"
                            for a in articles[:5])
            content = f"Stories the user is looking at:\n{ctx}\n\nUser question: {content}"
        msgs.append({"role": m["role"], "content": content})
    return msgs


def run_agent(llm: GroqClient, store: Store, settings: Settings, user_id: str, history: List[dict],
              articles: Optional[List[dict]] = None, runner: Optional[ToolRunner] = None) -> Iterator[Dict]:
    """Yields {"type": "text", "text"} and {"type": "tool", ...} events."""
    runner = runner or ToolRunner(store, llm, settings, user_id)
    try:
        followed = [s["topic"] for s in store.list_subscriptions(user_id)]
    except Exception:
        followed = []
    messages = build_messages(history, followed, articles or [])
    tools_ok = True

    for round_no in range(MAX_TOOL_ROUNDS + 1):
        use_tools = tools_ok and round_no < MAX_TOOL_ROUNDS
        final: Optional[Dict] = None
        try:
            for ev in llm.stream_chat(messages, tools=TOOL_SCHEMAS if use_tools else None):
                if ev["type"] == "text":
                    yield ev
                else:
                    final = ev
        except LLMError as e:
            if e.code == "tool_use_failed" and tools_ok:
                # The model produced a malformed tool call. Answer without tools, but do not let it
                # pretend an action happened.
                tools_ok = False
                messages.append({"role": "system", "content":
                                 "Tools are unavailable for this reply. Do not claim you followed or changed "
                                 "anything; suggest the Follow box in the Following tab instead."})
                continue
            raise
        if final is None:
            return
        calls = final["tool_calls"][:MAX_CALLS_PER_ROUND]
        if not calls or not use_tools:
            return
        messages.append({"role": "assistant", "content": final["content"] or None, "tool_calls": calls})
        for call in calls:
            name = call["function"]["name"]
            yield {"type": "tool", "name": name, "status": "start"}
            out = runner.run(name, call["function"]["arguments"])
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(out["result"], default=str)[:4000]})
            event = {"type": "tool", "name": name, "status": "done", "ok": bool(out["result"].get("ok"))}
            if out["event"]:
                event.update(topic=out["event"]["topic"], slug=out["event"]["slug"], changed=True)
            yield event
