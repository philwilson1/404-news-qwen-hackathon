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
HISTORY_CHARS = 2500


def system_prompt(followed: List[str]) -> str:
    topics = ", ".join(followed) if followed else "none yet"
    return (
        "You are 404 AI, the news assistant inside the 404 News app. "
        f"Today is {date.today().isoformat()}. No emoji.\n"
        f"Topics this user follows: {topics}.\n"
        "How to answer news questions (be detailed and thorough, not brief):\n"
        "- Open with a direct answer in 2 to 3 sentences that states the main takeaway.\n"
        "- Then cover 4 to 8 stories when the tools returned that many. For each story write a **bold headline in "
        "your own words**, then 2 to 4 sentences: what happened, who is involved, why it matters, and what to watch "
        "next when the source supports it. End the item with the outlet as a markdown link, e.g. [Reuters](https://...).\n"
        "- Group related stories under short ### headings and name the pattern when there is one.\n"
        "- Finish with a short 'What this means' paragraph (2 to 4 sentences) that connects the stories and points "
        "out the biggest implication or open question. Offer to go deeper on any one story.\n"
        "- Simple or conversational questions (greetings, how the app works) still get a short, direct answer.\n"
        "- NEVER print a bare URL. Links must be markdown with the outlet name as the link text.\n"
        "- Use only what the tools returned. Never invent quotes, numbers, or details. get_topic_news may return "
        "headlines only: in that case explain what each headline tells us and say plainly that the full detail is in "
        "the linked article, instead of guessing. get_category_news includes summaries, so use them fully.\n"
        "- If nothing relevant came back, say so plainly and suggest a narrower topic.\n"
        "- For health stories, report what the sources say and who it affects. Do not give personal medical advice or diagnoses; for symptoms or treatment questions, suggest seeing a doctor or pharmacist.\n"
        "Tools:\n"
        "- If the user pastes a message, forward or rumour, or asks whether something is true, real or fake, "
        "call check_claim (query = 3 to 8 keywords from the claim). If it returns a fact-check with "
        "link_readable true, call read_article on it to read the actual rating before you answer. Then reply "
        "in this shape: a bold verdict line using ONLY one of: **Reported by several outlets**, **Fact-checkers "
        "say this is false or misleading**, **Fact-checkers support this**, **Limited coverage so far**, "
        "**I could not confirm this**. Follow with 2 to 4 sentences on what was and was not found, with the "
        "outlets as markdown links, then one line on what to do before sharing it. Never call a claim simply "
        "true or false unless a fact-checker you read says so. Missing coverage is not proof it is false: say "
        "it may be too new or local. Never invent outlets, quotes or ratings.\n"
        "- If the user asks for more detail on one story ('tell me more', 'explain this', 'go deeper'), call "
        "read_article with that story's link (from a tool result or your earlier answer), then write a detailed "
        "explanation of 3 to 5 short paragraphs: what happened, background, who is affected, and what happens "
        "next, using only the article text. If read_article fails, say so and work from the headline and summary.\n"
        "- For anything about recent events, call a tool; do not answer from memory. For AI, technology, startups, "
        "world affairs or health call get_category_news first, and add get_topic_news for a specific angle.\n"
        "- If the user asks to follow, track, watch, or be kept in the loop on something, call follow_topic. Only "
        "say you are following a topic after the tool returned ok=true, then confirm in one line and show the top "
        "3 stories.\n"
    )


def build_messages(history: List[dict], followed: List[str], articles: List[dict]) -> List[dict]:
    msgs: List[dict] = [{"role": "system", "content": system_prompt(followed)}]
    trimmed = [m for m in history if m.get("role") in ("user", "assistant") and m.get("content")]
    trimmed = trimmed[-HISTORY_MESSAGES:]
    for i, m in enumerate(trimmed):
        content = str(m["content"])[:HISTORY_CHARS]
        if articles and i == len(trimmed) - 1 and m["role"] == "user":
            ctx = "\n".join(f"- {a.get('title', '')} ({a.get('source', '')}): {str(a.get('summary', ''))[:400]}"
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
                             "content": json.dumps(out["result"], default=str)[:7000]})
            event = {"type": "tool", "name": name, "status": "done", "ok": bool(out["result"].get("ok"))}
            if out["event"]:
                event.update(topic=out["event"]["topic"], slug=out["event"]["slug"], changed=True)
            yield event
