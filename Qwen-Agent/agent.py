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
        f"Today is {date.today().isoformat()}. No emoji.\n"
        f"Topics this user follows: {topics}.\n"
        "How to answer:\n"
        "- Lead with the answer in one sentence, then 3 to 6 bullets. Each bullet: a **bold headline in your own "
        "words**, one sentence on what happened, then the outlet as a markdown link, e.g. [Reuters](https://...).\n"
        "- NEVER print a bare URL. Links must be markdown with the outlet name as the link text.\n"
        "- Group related stories and name the pattern when there is one. Skip filler and repetition.\n"
        "- Use only what the tools returned. get_topic_news returns headlines only, so say when detail is missing "
        "instead of guessing. get_category_news includes summaries.\n"
        "- If nothing relevant came back, say so plainly and suggest a narrower topic.\n"
        "Tools:\n"
        "- For anything about recent events, call a tool; do not answer from memory. For AI, technology, startups "
        "or world affairs call get_category_news first, and add get_topic_news for a specific angle.\n"
        "- If the user asks to follow, track, watch, or be kept in the loop on something, call follow_topic. Only "
        "say you are following a topic after the tool returned ok=true, then confirm in one line and show the top "
        "3 stories."
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
