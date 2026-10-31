"""AI drafting for the Cybersecurity breach library.

Takes a few report links, reads them, asks the model to fill in a breach card in the SAME
shape as the hand-built Binance card, checks the result, and saves it as a DRAFT.

Hard rules (they match the plan):
  * The AI can never publish. Rows are always saved with status 'draft'.
  * Source links come from the pages we actually opened, never from the model.
  * Numbers in the card that do not appear in the sources are flagged for review.
"""
import datetime as dt
import json
import re
from typing import Callable, Dict, List, Optional

import reader
from config import Settings
from llm import GroqClient, LLMError

MAX_URLS = 3
SOURCE_CHARS = 3500

STAGES = ["Recon and staging", "Initial access", "Foothold", "Escalation", "Action", "Laundering", "Exfiltration"]
ATTACK_ID = re.compile(r"^T\d{4}(\.\d{3})?$")

# The Binance card, exactly as it was published. It is the template every draft must follow.
EXAMPLE_CARD = {
    "headline": "Hackers stole $6.3bn from Binance in 20 minutes",
    "source_label": "TRM Labs · Oct 29, 2026",
    "occurred_on": "2026-10-29",
    "what_happened": "On Oct 29, 2026, an attacker moved about $6.36bn out of Binance wallets on ten blockchains, most of it in about 20 minutes. It is the largest crypto theft on record. TRM Labs and Chainalysis say North Korea's TraderTraitor hacking unit was behind it. About $2.7bn has been frozen so far.",
    "affected": "Binance says user funds are safe and it has set aside over $6.34bn of company funds to cover the loss. It paused withdrawals on several networks. The investigation is still developing, so check Binance's official statements for updates.",
    "what_to_do": "Only trust Binance's official channels, and ignore messages about the hack asking for your password or codes. Turn on 2FA and an anti-phishing code, use a unique password, and don't keep all your crypto on one platform.",
    "attacker": "TraderTraitor (North Korea)",
    "attacker_assessed_by": "TRM Labs and Chainalysis, high confidence. Binance has not attributed the attack itself.",
    "attack_chain": [
        {"stage": "Recon and staging", "detail": "Small Tornado Cash withdrawals funded an operator wallet from Oct 28. The attack code was tested and rehearsed on other wallets at least 36 hours before the theft.", "attack_ids": [], "soc_view": "Watch for new wallets and contract deployments that interact with your treasury addresses."},
        {"stage": "Initial access", "detail": "Not confirmed. Binance said an early look pointed to a compromised laptop, then found more points of breach.", "attack_ids": [], "soc_view": "Alert on unusual signing requests."},
        {"stage": "Action", "detail": "From 20:05 UTC on Oct 29, about $6.36bn left Binance wallets on ten blockchains, most of it in about 20 minutes.", "attack_ids": ["T1657"], "soc_view": None},
        {"stage": "Laundering", "detail": "The attacker sold stablecoins to market makers at a steep discount and split Bitcoin through a peel chain. About $2.7bn was frozen.", "attack_ids": [], "soc_view": "Screen deposits against the labeled attacker addresses."},
    ],
    "lessons": ["Monitor treasury wallets for unexpected delegations and alert on any.", "Separate signing infrastructure by chain and wallet tier."],
    "root_cause": "unconfirmed",
}

SYSTEM_PROMPT = """You write breach cards for 404 News, a public news app. Readers range from people who only want to know "was I affected?" to SOC analysts. Accuracy matters more than anything: a wrong card hurts real people.

Use ONLY facts stated in the SOURCES below. If the sources do not say something, leave it out, write "Not reported in the sources.", or use an empty list. Never guess, never fill gaps from memory.

Rules:
1. Plain layer first. headline, what_happened, affected and what_to_do use short, simple words. No unexplained jargon: if you must use a technical term, explain it in a few words.
2. headline: one line with the main number, under 120 characters.
3. what_happened: 2 to 3 sentences: what happened, how big, who is blamed and by whom.
4. affected: what the victim company says about customer money or data. If the sources do not say, say to check the company's official statement.
5. what_to_do: 2 practical steps an ordinary person can take.
6. Attribution is never stated as fact. Write who assesses it ("assessed by X"). attacker is the group name and country only if the sources give them.
7. root_cause is "confirmed" ONLY if the victim company or official investigators confirmed it in the sources. Otherwise "unconfirmed".
8. attack_chain: only stages the sources describe, in order, using these stage names: Recon and staging, Initial access, Foothold, Escalation, Action, Laundering, Exfiltration. Skip stages the sources say nothing about.
9. attack_ids: ATT&CK technique IDs (like T1657) ONLY if a source names them. Otherwise an empty list.
10. soc_view: a defensive detection idea taken from the sources' own advice, or null.
11. lessons: defences the sources recommend. An empty list if there are none.
12. Do not help attackers: no wallet addresses, keys, exploit code or step-by-step ways to repeat the attack. Describe at concept level.
13. occurred_on is an ISO date (YYYY-MM-DD) only if the sources state it, else null. source_label is "<publisher> · <date>".

Reply with ONE JSON object and nothing else, with exactly these keys:
headline, source_label, occurred_on, what_happened, affected, what_to_do, attacker, attacker_assessed_by, attack_chain (list of {stage, detail, attack_ids, soc_view}), lessons (list of strings), root_cause.

Here is a finished card. Match its shape, length and tone:
""" + json.dumps(EXAMPLE_CARD, ensure_ascii=False)


class DraftError(Exception):
    """Message is safe to return to the admin."""


def slugify(text: str, limit: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].strip("-") or "breach"


def _clip(v, n: int) -> str:
    return " ".join(str(v or "").split())[:n]


def parse_json(raw: str) -> dict:
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    obj = json.loads(text[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("JSON is not an object")
    return obj


def validate_card(obj: dict) -> dict:
    """Keep only known fields, enforce types and limits. Raises DraftError if the card is unusable."""
    headline = _clip(obj.get("headline"), 160)
    what = _clip(obj.get("what_happened"), 900)
    if len(headline) < 8 or not what:
        raise DraftError("The AI did not produce a usable headline and summary.")

    occurred = None
    try:
        occurred = dt.date.fromisoformat(str(obj.get("occurred_on") or "")).isoformat()
    except ValueError:
        pass

    chain, seen = [], set()
    for st in obj.get("attack_chain") or []:
        if not isinstance(st, dict):
            continue
        name = next((s for s in STAGES if s.lower() == str(st.get("stage", "")).strip().lower()), None)
        if not name or name in seen:
            continue
        seen.add(name)
        ids = [i for i in (st.get("attack_ids") or []) if isinstance(i, str) and ATTACK_ID.match(i.strip())]
        chain.append({"stage": name, "detail": _clip(st.get("detail"), 600) or None,
                      "attack_ids": [i.strip() for i in ids][:6], "soc_view": _clip(st.get("soc_view"), 400) or None})
    chain.sort(key=lambda s: STAGES.index(s["stage"]))

    lessons = [_clip(x, 300) for x in (obj.get("lessons") or []) if _clip(x, 300)][:8]
    return {
        "headline": headline,
        "source_label": _clip(obj.get("source_label"), 80),
        "occurred_on": occurred,
        "what_happened": what,
        "affected": _clip(obj.get("affected"), 600),
        "what_to_do": _clip(obj.get("what_to_do"), 500),
        "attacker": _clip(obj.get("attacker"), 120) or None,
        "attacker_assessed_by": _clip(obj.get("attacker_assessed_by"), 200) or None,
        "attack_chain": chain,
        "lessons": lessons,
        "root_cause": "confirmed" if obj.get("root_cause") == "confirmed" else "unconfirmed",
    }


def ungrounded_numbers(card: dict, source_text: str) -> List[str]:
    """Numbers that appear in the card but nowhere in the sources: the classic AI invention."""
    parts = [card["headline"], card["what_happened"], card["affected"], card["what_to_do"]]
    parts += [(s["detail"] or "") + " " + (s["soc_view"] or "") for s in card["attack_chain"]]
    flat = source_text.replace(",", "")
    bad = []
    for tok in re.findall(r"\d[\d,]*\.?\d*", " ".join(parts)):
        t = tok.replace(",", "").rstrip(".")
        if len(t) >= 2 and t not in flat and t not in bad:
            bad.append(t)
    return bad


def _read_sources(urls: List[str], fetch: Callable) -> List[dict]:
    pages, problems = [], []
    for url in urls:
        try:
            page = fetch(url, SOURCE_CHARS)
            pages.append({"title": page["title"] or page.get("host", url), "url": url, "text": page["text"]})
        except reader.ReaderError as e:
            problems.append(f"{url}: {e}")
    if not pages:
        raise DraftError("Could not read any of those links. " + " | ".join(problems))
    return pages


def draft_breach(llm: GroqClient, store, settings: Settings, urls: List[str], note: str = "",
                 fetch: Callable = reader.fetch_article_text, today: Optional[dt.date] = None) -> Dict:
    urls = [u.strip() for u in urls if isinstance(u, str) and u.strip()]
    urls = list(dict.fromkeys(urls))[:MAX_URLS]
    if not urls:
        raise DraftError("Send at least one report link.")
    pages = _read_sources(urls, fetch)
    source_text = "\n\n".join(p["text"] for p in pages)

    sources_block = "\n\n".join(f"SOURCE {i + 1}: {p['title']}\nURL: {p['url']}\n{p['text']}" for i, p in enumerate(pages))
    user_msg = f"SOURCES\n\n{sources_block}\n\n" + (f"Editor note: {_clip(note, 300)}\n\n" if note else "") + \
        "Write the breach card as one JSON object."
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_msg}]

    card = None
    for attempt in range(2):
        try:
            out = llm.complete(messages, model=settings.model, max_tokens=2500, temperature=0.2)
        except LLMError as e:
            raise DraftError(e.public_message)
        try:
            card = validate_card(parse_json(out["content"]))
            break
        except (ValueError, DraftError) as e:
            if attempt == 1:
                raise DraftError(f"The AI's answer could not be read as a card ({e}). Try again.")
            messages += [{"role": "assistant", "content": out["content"]},
                         {"role": "user", "content": "That was not valid. Reply with ONE JSON object only, using exactly the keys listed."}]

    warnings = []
    bad = ungrounded_numbers(card, source_text)
    if bad:
        warnings.append("Numbers not found in the sources, check them: " + ", ".join(bad))
    if len(pages) < 2:
        warnings.append("Only one source was read. Add a second independent report before publishing.")
    if len(pages) < len(urls):
        warnings.append(f"{len(urls) - len(pages)} link(s) could not be read and are not listed as sources.")
    if not card["attack_chain"]:
        warnings.append("The sources described no attack stages. The analyst view will be empty.")

    base = slugify(card["headline"])
    slug, n = base, 2
    while store.breach_slug_exists(slug):
        slug, n = f"{base}-{n}", n + 1

    row = dict(card, slug=slug, status="draft",  # always a draft: a human publishes
               sources=[{"title": _clip(p["title"], 200), "url": p["url"]} for p in pages],
               last_checked_on=(today or dt.date.today()).isoformat())
    store.insert_breach(row)
    return {"slug": slug, "status": "draft", "warnings": warnings, "card": row}
