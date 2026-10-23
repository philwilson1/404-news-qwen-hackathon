-- Run once in the Supabase SQL editor. Safe to re-run.
-- Adds "follow a topic" support. It does not change your existing tables.

-- 1. Which topics each user follows -------------------------------------------------
create table if not exists public.topic_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  topic text not null check (char_length(topic) between 2 and 60),
  slug text not null check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' and char_length(slug) <= 60),
  query text not null check (char_length(query) between 2 and 120),
  created_at timestamptz not null default now(),
  last_refreshed_at timestamptz,
  unique (user_id, slug)
);

alter table public.topic_subscriptions enable row level security;

drop policy if exists "own topics: select" on public.topic_subscriptions;
drop policy if exists "own topics: insert" on public.topic_subscriptions;
drop policy if exists "own topics: delete" on public.topic_subscriptions;
create policy "own topics: select" on public.topic_subscriptions for select using (auth.uid() = user_id);
create policy "own topics: insert" on public.topic_subscriptions for insert with check (auth.uid() = user_id);
create policy "own topics: delete" on public.topic_subscriptions for delete using (auth.uid() = user_id);

-- Max 10 topics per user (keep in sync with MAX_TOPICS_PER_USER in the backend).
create or replace function public.enforce_topic_limit() returns trigger
language plpgsql as $$
begin
  if (select count(*) from public.topic_subscriptions where user_id = new.user_id) >= 10 then
    raise exception 'topic limit reached (10)';
  end if;
  return new;
end $$;

drop trigger if exists topic_limit on public.topic_subscriptions;
create trigger topic_limit before insert on public.topic_subscriptions
  for each row execute function public.enforce_topic_limit();

-- 2. Digests: one per topic, shared by everyone who follows it ------------------------
-- Written only by the backend (service key bypasses RLS). Users can read digests of topics they follow.
create table if not exists public.topic_digests (
  id uuid primary key default gen_random_uuid(),
  slug text not null,
  topic text not null,
  content text not null,
  headlines jsonb not null default '[]'::jsonb,
  article_count int not null default 0,
  model text,
  created_at timestamptz not null default now()
);
create index if not exists topic_digests_slug_created on public.topic_digests (slug, created_at desc);

alter table public.topic_digests enable row level security;
drop policy if exists "followers read digests" on public.topic_digests;
create policy "followers read digests" on public.topic_digests for select using (
  exists (select 1 from public.topic_subscriptions s
          where s.user_id = auth.uid() and s.slug = topic_digests.slug)
);

-- 3. Faster topic feeds on your existing articles table --------------------------------
create index if not exists articles_category_created on public.articles (category, created_at desc);
