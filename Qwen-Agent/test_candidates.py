from datetime import datetime, timezone
import candidates as c

NOW = datetime(2026, 10, 31, tzinfo=timezone.utc)
def d(day): return f"Fri, {day} Oct 2026 10:00:00 +0000"
FEEDS = {
 "A": [{"title": "Hackers steal $6.3bn from Binance in record crypto heist", "link": "https://a.com/1", "published": d(30), "summary": ""},
       {"title": "Join our webinar on breach response", "link": "https://a.com/2", "published": d(30), "summary": ""},
       {"title": "Old breach at Acme exposed data", "link": "https://a.com/3", "published": "Mon, 01 Sep 2026 10:00:00 +0000", "summary": ""},
       {"title": "New phone review", "link": "https://a.com/4", "published": d(30), "summary": ""}],
 "B": [{"title": "Binance hack: North Korean hackers steal $6.3bn in crypto", "link": "https://b.com/1", "published": d(30), "summary": ""},
       {"title": "Retailer Zeta breached, 4 million customer records leaked", "link": "https://b.com/2", "published": d(29), "summary": ""}],
 "C": [{"title": "Retailer Zeta breached, 4 million customer records leaked online", "link": "https://c.com/9", "published": d(29), "summary": ""}],
}
def load(name, url): 
    if name == "D": raise RuntimeError("down")
    return FEEDS[name]
feeds = [("A","u"),("B","u"),("C","u"),("D","u")]

r = c.find_candidates(set(), feeds=feeds, load=load, now=NOW)
titles = [x["title"] for x in r["candidates"]]
assert len(r["candidates"]) == 2, titles                       # webinar, old, unrelated all dropped; stories grouped
assert r["candidates"][0]["outlets"] == 2 and r["candidates"][0]["corroborated"]
assert r["feeds_failed"] == ["D"]                              # a dead feed never breaks the list
assert set(r["candidates"][0]["draft_urls"]) <= {"https://a.com/1","https://b.com/1","https://b.com/2","https://c.com/9"}
r2 = c.find_candidates({"https://a.com/1"}, feeds=feeds, load=load, now=NOW)
assert len(r2["candidates"]) == 1 and "Zeta" in r2["candidates"][0]["title"]   # already-used story hidden
r3 = c.find_candidates(set(), feeds=feeds, load=load, now=NOW, min_outlets=2)
assert len(r3["candidates"]) == 2
print("candidate tests passed")
