import { useState, useEffect, useCallback } from 'react';
import { Plus, RefreshCw, X, BellRing, ExternalLink, ChevronDown, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import {
  fetchTopics, fetchLatestDigests, fetchTopicArticles, followTopic, unfollowTopic, refreshTopic,
  MAX_TOPICS, type Topic, type Digest, type Article,
} from '../lib/supabase';
import ArticleDetail from './ArticleDetail';

const STARTERS = ['Cybersecurity', 'Nigerian fintech', 'Quantum computing', 'Premier League', 'Climate tech'];

function timeAgo(iso?: string | null): string {
  if (!iso) return 'never';
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

function articleLink(a: Article): string | undefined {
  return a.agent_log?.find((l) => l.link)?.link;
}

export default function TopicsView() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [digests, setDigests] = useState<Record<string, Digest>>({});
  const [stories, setStories] = useState<Record<string, Article[]>>({});
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState('');
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [message, setMessage] = useState<{ kind: 'error' | 'info'; text: string } | null>(null);
  const [selected, setSelected] = useState<Article | null>(null);

  const load = useCallback(async () => {
    const t = await fetchTopics();
    setTopics(t);
    const slugs = t.map((x) => x.slug);
    const [d, s] = await Promise.all([fetchLatestDigests(slugs), fetchTopicArticles(slugs)]);
    setDigests(d);
    setStories(s);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const setBusyFlag = (slug: string, on: boolean) =>
    setBusy((prev) => { const next = new Set(prev); if (on) next.add(slug); else next.delete(slug); return next; });

  const refresh = async (slug: string) => {
    setBusyFlag(slug, true);
    const res = await refreshTopic(slug);
    if (res.error) setMessage({ kind: 'error', text: res.error });
    await load();
    setBusyFlag(slug, false);
  };

  const handleFollow = async (name: string) => {
    const value = name.trim();
    if (!value || adding) return;
    setAdding(true);
    setMessage(null);
    const res = await followTopic(value);
    if (res.error || !res.slug) {
      setMessage({ kind: 'error', text: res.error ?? 'Could not follow that topic.' });
      setAdding(false);
      return;
    }
    setInput('');
    await load();
    setAdding(false);
    setMessage({ kind: 'info', text: `Following ${value}. Fetching the first stories...` });
    await refresh(res.slug);
    setMessage(null);
  };

  const handleUnfollow = async (t: Topic) => {
    const res = await unfollowTopic(t.slug);
    if (res.error) { setMessage({ kind: 'error', text: res.error }); return; }
    setTopics((prev) => prev.filter((x) => x.slug !== t.slug));
  };

  const toggleExpanded = (slug: string) =>
    setExpanded((prev) => { const next = new Set(prev); if (next.has(slug)) next.delete(slug); else next.add(slug); return next; });

  return (
    <div className="pt-4 pb-24 px-4">
      <div className="mb-4">
        <h2 className="text-white font-bold text-lg leading-tight">Following</h2>
        <p className="text-xs text-zinc-500">Topics your agent keeps an eye on. {topics.length}/{MAX_TOPICS} followed.</p>
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); handleFollow(input); }}
        className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-2xl p-2 mb-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Follow a topic, e.g. space exploration"
          maxLength={60}
          disabled={adding}
          className="flex-1 bg-transparent text-white text-sm placeholder:text-zinc-600 outline-none px-2 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={adding || !input.trim()}
          aria-label="Follow topic"
          className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center text-white disabled:opacity-40"
        >
          {adding ? <Loader2 size={15} className="animate-spin" /> : <Plus size={16} />}
        </button>
      </form>

      {message && (
        <p className={`text-xs mb-3 px-1 ${message.kind === 'error' ? 'text-rose-400' : 'text-sky-400'}`}>{message.text}</p>
      )}

      {loading ? (
        <div className="space-y-3">{[1, 2].map((i) => <div key={i} className="h-40 rounded-2xl bg-zinc-900 animate-pulse" />)}</div>
      ) : topics.length === 0 ? (
        <div className="text-center py-10">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/20 mb-3">
            <BellRing size={24} className="text-sky-400" />
          </div>
          <p className="text-white font-semibold">Nothing followed yet</p>
          <p className="text-zinc-500 text-sm mt-1 mb-4">Pick a topic and 404 AI will keep fresh stories and a short briefing here. You can also ask in the AI tab: "keep me in the loop on cybersecurity".</p>
          <div className="flex flex-wrap justify-center gap-2">
            {STARTERS.map((s) => (
              <button key={s} onClick={() => handleFollow(s)} disabled={adding}
                className="px-3 py-1.5 rounded-full text-xs font-semibold bg-zinc-900 border border-zinc-800 text-zinc-300 hover:border-sky-500/40 disabled:opacity-50">
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {topics.map((t) => {
            const digest = digests[t.slug];
            const list = stories[t.slug] ?? [];
            const isBusy = busy.has(t.slug);
            const open = expanded.has(t.slug);
            const shown = open ? list : list.slice(0, 3);
            return (
              <section key={t.id} className="rounded-2xl bg-zinc-900/60 border border-zinc-800 p-4">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="min-w-0">
                    <h3 className="text-white font-bold text-base truncate">{t.topic}</h3>
                    <p className="text-[11px] text-zinc-500">Updated {timeAgo(digest?.created_at ?? t.last_refreshed_at)}</p>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button onClick={() => refresh(t.slug)} disabled={isBusy} aria-label={`Refresh ${t.topic}`}
                      className="p-2 text-zinc-400 hover:text-sky-400 disabled:text-zinc-700">
                      <RefreshCw size={15} className={isBusy ? 'animate-spin' : ''} />
                    </button>
                    <button onClick={() => handleUnfollow(t)} aria-label={`Unfollow ${t.topic}`}
                      className="p-2 text-zinc-500 hover:text-rose-400">
                      <X size={16} />
                    </button>
                  </div>
                </div>

                {digest ? (
                  <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none mb-3">
                    <ReactMarkdown>{digest.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm text-zinc-500 mb-3">
                    {isBusy ? 'Fetching the first stories...' : 'No briefing yet. Tap refresh to fetch the first stories.'}
                  </p>
                )}

                {shown.length > 0 && (
                  <ul className="divide-y divide-zinc-800 border-t border-zinc-800">
                    {shown.map((a) => {
                      const link = articleLink(a);
                      return (
                        <li key={a.id} className="py-2.5 flex items-start gap-2">
                          <button onClick={() => setSelected(a)} className="flex-1 min-w-0 text-left">
                            <p className="text-white text-sm font-medium leading-snug line-clamp-2">{a.title}</p>
                            <p className="text-[11px] text-zinc-500 mt-0.5">{a.source} &middot; {timeAgo(a.created_at)}</p>
                          </button>
                          {link && (
                            <a href={link} target="_blank" rel="noopener noreferrer" aria-label="Open original story"
                              className="p-1.5 text-zinc-500 hover:text-sky-400 flex-shrink-0">
                              <ExternalLink size={14} />
                            </a>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
                {list.length > 3 && (
                  <button onClick={() => toggleExpanded(t.slug)} className="flex items-center gap-1 text-xs text-sky-400 font-medium mt-1">
                    <ChevronDown size={13} className={open ? 'rotate-180 transition-transform' : 'transition-transform'} />
                    {open ? 'Show fewer' : `Show all ${list.length} stories`}
                  </button>
                )}
              </section>
            );
          })}
        </div>
      )}

      <ArticleDetail article={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
