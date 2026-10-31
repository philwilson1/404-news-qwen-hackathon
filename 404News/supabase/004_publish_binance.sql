-- Run once in the Supabase SQL editor after 003_breaches.sql. Safe to re-run.
-- Fills in and publishes the Binance card with the researched facts and real source links.
-- Facts come from TRM Labs (Oct 29-30, 2026), Al Jazeera, CBC and NPR. TRM's page says Binance
-- has not published a root cause, so the cause stays 'unconfirmed'. Re-check before each re-run.

insert into public.breaches
  (slug, status, headline, source_label, occurred_on, what_happened, affected, what_to_do,
   attacker, attacker_assessed_by, attack_chain, lessons, root_cause, sources, last_checked_on)
values (
  'binance-oct-2026', 'published',
  $q$Hackers stole $6.3bn from Binance in 20 minutes$q$,
  $q$TRM Labs · Oct 29, 2026$q$,
  '2026-10-29',
  $q$On Oct 29, 2026, an attacker moved about $6.36bn out of Binance wallets on ten blockchains, most of it in about 20 minutes. It is the largest crypto theft on record. TRM Labs and Chainalysis say North Korea's TraderTraitor hacking unit was behind it. About $2.7bn has been frozen so far.$q$,
  $q$Binance says user funds are safe and it has set aside over $6.34bn of company funds to cover the loss. It paused withdrawals on several networks. The investigation is still developing, so check Binance's official statements for updates.$q$,
  $q$Only trust Binance's official channels, and ignore messages about the hack asking for your password or codes. Turn on 2FA and an anti-phishing code, use a unique password, and don't keep all your crypto on one platform.$q$,
  $q$TraderTraitor (North Korea)$q$,
  $q$TRM Labs and Chainalysis, high confidence. Binance has not attributed the attack itself.$q$,
  $q$[{"stage": "Recon and staging", "detail": "Small Tornado Cash withdrawals funded an operator wallet from Oct 28. The attack code was tested and rehearsed on other wallets at least 36 hours before the theft.", "attack_ids": [], "soc_view": "Watch for new wallets and contract deployments that interact with your treasury addresses."}, {"stage": "Initial access", "detail": "Not confirmed. Binance said an early look pointed to a compromised laptop, then found more points of breach. TRM assesses the attacker gained the ability to make Binance's hot wallet signing system sign transactions of its choosing.", "attack_ids": [], "soc_view": "Alert on unusual signing requests. TRM advises separating signing paths by chain and wallet tier."}, {"stage": "Foothold", "detail": "On Ethereum, 50 pre-signed EIP-7702 authorizations turned a Binance hot wallet into a sweeper that only the attacker could call. The delegation stayed in place and swept new deposits again and again.", "attack_ids": [], "soc_view": "Alert on any EIP-7702 delegation on a treasury wallet. It shows up as code at an address that should have none."}, {"stage": "Escalation", "detail": "Wallets on ten chains with different key types produced valid signatures for the attacker within about half an hour (TRM's assessment).", "attack_ids": [], "soc_view": "Reject unexpected authorizations. A request for many authorizations across a range of transaction counts is an indicator of compromise."}, {"stage": "Action", "detail": "From 20:05 UTC on Oct 29, about $6.36bn left Binance wallets on ten blockchains, most of it in about 20 minutes.", "attack_ids": ["T1657"], "soc_view": "Real-time outflow alerts per wallet, with automatic withdrawal pauses."}, {"stage": "Laundering", "detail": "The attacker sold stablecoins to market makers at a steep discount, borrowed ETH on Aave and split Bitcoin through a peel chain. About $2.7bn was frozen. TRM says the attacker still held about $2.4bn as of Oct 30.", "attack_ids": [], "soc_view": "Screen deposits and counterparties against the labeled attacker addresses."}]$q$::jsonb,
  $q$["Monitor treasury wallets for EIP-7702 delegations and alert on any.", "Keep a tested, pre-approved way to sign a revocation.", "Reject EIP-7702 authorizations unless they are expected.", "Separate signing infrastructure and approval paths by chain and wallet tier."]$q$::jsonb,
  'unconfirmed',
  $q$[{"title": "TRM Labs: North Korea steals USD 6.36 billion from Binance", "url": "https://www.trmlabs.com/resources/blog/north-korea-steals-usd-6-36-billion-from-binance-in-the-largest-hack-in-history"}, {"title": "Al Jazeera: Binance says $6.3bn stolen in biggest crypto heist in history", "url": "https://www.aljazeera.com/news/2026/10/30/binance-says-6-3bn-stolen-in-biggest-crypto-heist-in-history-what-we-know"}, {"title": "CBC: Binance says $6.3B US hacked", "url": "https://www.cbc.ca/news/business/binance-north-korea-9.7402446"}, {"title": "NPR: Blockchain intelligence firms link North Korea to $6.3B hack on Binance", "url": "https://www.npr.org/2026/10/30/g-s1-150902/blockchain-intelligence-firms-link-north-korea-to-6-3b-hack-on-binance"}]$q$::jsonb,
  current_date
)
on conflict (slug) do update set
  status = excluded.status, headline = excluded.headline, source_label = excluded.source_label,
  occurred_on = excluded.occurred_on, what_happened = excluded.what_happened,
  affected = excluded.affected, what_to_do = excluded.what_to_do, attacker = excluded.attacker,
  attacker_assessed_by = excluded.attacker_assessed_by, attack_chain = excluded.attack_chain,
  lessons = excluded.lessons, root_cause = excluded.root_cause, sources = excluded.sources,
  last_checked_on = excluded.last_checked_on;
