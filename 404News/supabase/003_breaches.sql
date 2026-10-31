-- Run once in the Supabase SQL editor. Safe to re-run.
-- Cybersecurity breach library. Cards are written by hand (or drafted by AI) as 'draft',
-- checked by you, then moved to 'published'. The app can only ever read published rows.

create table if not exists public.breaches (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' and char_length(slug) <= 80),
  status text not null default 'draft' check (status in ('draft', 'reviewed', 'published')),

  -- Simple layer
  headline text not null check (char_length(headline) between 8 and 160),
  source_label text not null default '',            -- e.g. 'TRM Labs · Oct 2026'
  occurred_on date,
  what_happened text not null,
  affected text not null default '',
  what_to_do text not null default '',

  -- Analyst layer
  attacker text,
  attacker_assessed_by text,
  attack_chain jsonb not null default '[]'::jsonb,  -- [{stage, detail, attack_ids:[], soc_view}]
  lessons jsonb not null default '[]'::jsonb,       -- ["..."]

  -- Both layers
  root_cause text not null default 'unconfirmed' check (root_cause in ('confirmed', 'unconfirmed')),
  sources jsonb not null default '[]'::jsonb,       -- [{title, url}]
  last_checked_on date not null default current_date,
  created_at timestamptz not null default now()
);

create index if not exists breaches_published on public.breaches (status, occurred_on desc);

-- Rule: a card without a source link cannot be published.
create or replace function public.enforce_breach_sources() returns trigger
language plpgsql as $$
begin
  if new.status = 'published' then
    if jsonb_typeof(new.sources) <> 'array' or jsonb_array_length(new.sources) = 0 then
      raise exception 'cannot publish: add at least one source';
    end if;
    if exists (select 1 from jsonb_array_elements(new.sources) s where coalesce(s->>'url', '') !~ '^https?://') then
      raise exception 'cannot publish: every source needs an http(s) url';
    end if;
  end if;
  return new;
end $$;

drop trigger if exists breach_sources_required on public.breaches;
create trigger breach_sources_required before insert or update on public.breaches
  for each row execute function public.enforce_breach_sources();

-- Readers only ever see published rows. Writes happen in the SQL editor or with the service key.
alter table public.breaches enable row level security;
drop policy if exists "published breaches are readable" on public.breaches;
create policy "published breaches are readable" on public.breaches
  for select using (status = 'published');

-- First card: Binance, as a DRAFT. Facts below come only from your plan notes.
-- Add the real source URLs, check every line, then run the publish statement at the bottom.
insert into public.breaches
  (slug, status, headline, source_label, what_happened, affected, what_to_do,
   attacker, attacker_assessed_by, attack_chain, lessons, root_cause, sources)
values (
  'binance-oct-2026', 'draft',
  'Hackers stole $6.3bn from Binance in 20 minutes',
  'TRM Labs · Oct 2026',
  'Attackers moved about $6.3bn of crypto out of the exchange in roughly 20 minutes, reported as the biggest crypto heist in history. TRM Labs assesses North Korea was behind it.',
  'DRAFT: confirm from Binance''s own statement whether customer funds or data were touched.',
  'Use a unique password, turn on 2FA, and don''t keep all your money on one platform.',
  'North Korea (group not yet confirmed)', 'TRM Labs',
  '[{"stage":"Recon"},{"stage":"Initial access"},{"stage":"Foothold"},{"stage":"Escalation"},{"stage":"Action"},{"stage":"Laundering"}]'::jsonb,
  '[]'::jsonb,
  'unconfirmed',
  '[{"title":"TRM Labs: North Korea steals USD 6.36 billion from Binance","url":""},
    {"title":"Al Jazeera: Binance says $6.3bn stolen in biggest crypto heist in history","url":""}]'::jsonb
)
on conflict (slug) do nothing;

-- To publish after review (fails on purpose until every source has a url):
-- update public.breaches set status = 'published', last_checked_on = current_date where slug = 'binance-oct-2026';
