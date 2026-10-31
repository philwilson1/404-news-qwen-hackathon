import json
import breach_draft as bd
from config import Settings
from store import MemoryStore

SRC = ("On October 29, 2026, an attacker moved approximately 6.36 billion out of wallets on ten blockchains, "
       "most of it in about 20 minutes. About 2.7 billion has been frozen. TraderTraitor is blamed by TRM Labs. " * 3)

def fetch(url, n):
    if "bad" in url:
        raise bd.reader.ReaderError("blocked")
    return {"title": "Report " + url[-1], "text": SRC, "host": "x.com"}

class FakeLLM:
    def __init__(self, replies): self.replies, self.calls = list(replies), 0
    def complete(self, messages, **kw):
        self.calls += 1
        return {"content": self.replies.pop(0), "tool_calls": [], "model": "fake"}

GOOD = json.dumps({
    "headline": "Hackers stole $6.36bn in 20 minutes", "source_label": "TRM Labs · Oct 29, 2026", "occurred_on": "2026-10-29",
    "what_happened": "An attacker moved about 6.36 billion in 20 minutes. About 9.9 billion more was lost.",
    "affected": "Check the official statement.", "what_to_do": "Turn on 2FA.", "attacker": "TraderTraitor", "attacker_assessed_by": "TRM Labs",
    "attack_chain": [{"stage": "action", "detail": "Moved funds", "attack_ids": ["T1657", "bogus"], "soc_view": None},
                     {"stage": "Recon and staging", "detail": "Prep", "attack_ids": [], "soc_view": None},
                     {"stage": "Made up stage", "detail": "x", "attack_ids": [], "soc_view": None}],
    "lessons": ["Monitor wallets"], "root_cause": "banana", "status": "published", "sources": [{"url": "http://evil"}]})

s = Settings()
store = MemoryStore()
r = bd.draft_breach(FakeLLM(["```json\n" + GOOD + "\n```"]), store, s, ["https://a.com/1", "https://b.com/2", "https://bad.com/3"], fetch=fetch)
row = store.breaches[0]
assert row["status"] == "draft", row["status"]                      # model said published, we force draft
assert row["root_cause"] == "unconfirmed"                           # bad value falls back
assert [x["stage"] for x in row["attack_chain"]] == ["Recon and staging", "Action"]   # ordered, invented stage dropped
assert row["attack_chain"][1]["attack_ids"] == ["T1657"]            # bogus ID dropped
assert [x["url"] for x in row["sources"]] == ["https://a.com/1", "https://b.com/2"]   # only pages we read
assert any("9.9" in w for w in r["warnings"]), r["warnings"]        # invented number flagged
assert any("could not be read" in w for w in r["warnings"])
assert row["slug"] == "hackers-stole-6-36bn-in-20-minutes"
# retry on bad JSON, then slug dedupe
llm = FakeLLM(["not json", GOOD]); bd.draft_breach(llm, store, s, ["https://a.com/1"], fetch=fetch)
assert llm.calls == 2 and store.breaches[1]["slug"].endswith("-2")
# failures
for bad_urls in ([], ["https://bad.com/1"]):
    try: bd.draft_breach(FakeLLM([GOOD]), store, s, bad_urls, fetch=fetch); raise SystemExit("should fail")
    except bd.DraftError: pass
try: bd.draft_breach(FakeLLM(["nope", "nope"]), store, s, ["https://a.com/1"], fetch=fetch); raise SystemExit("should fail")
except bd.DraftError: pass
print("all tests passed; prompt chars:", len(bd.SYSTEM_PROMPT))
