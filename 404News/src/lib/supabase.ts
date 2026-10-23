import { createClient, type SupabaseClient, type User } from '@supabase/supabase-js';
import { fallbackArticles, fallbackAgentRuns } from '../data/fallback';

// ============================================
// TYPES
// ============================================

export interface Article {
  id: string; title: string; summary: string; source: string; source_logo: string;
  author: string; vibe: string; tag: string; verified: boolean; confidence: number;
  image_url: string; views: string; trending: boolean; published_at: string;
  read_time: number; agent_log: AgentLogEntry[] | null; created_at: string;
  category?: 'tech' | 'geopolitics' | 'startups' | string;
}
export interface AgentLogEntry { agent: string; status: string; detail: string; link?: string; }
export interface Bookmark { id: string; article_id: string; title: string; user_id?: string; created_at: string; }
export interface ChatMessage { id: string; role: 'user' | 'assistant'; content: string; sources: Article[] | null; user_id?: string; created_at: string; }
export interface Topic { id: string; user_id: string; topic: string; slug: string; query: string; created_at: string; last_refreshed_at: string | null; }
export interface DigestHeadline { title: string; source: string; link: string; published: string; }
export interface Digest { id: string; slug: string; topic: string; content: string; headlines: DigestHeadline[]; article_count: number; model: string | null; created_at: string; }
export interface ChatEvent { event: 'tool'; name: string; status: 'start' | 'done'; ok?: boolean; changed?: boolean; topic?: string; slug?: string; }
export interface AgentRun { id: string; agent_name: string; status: string; items_processed: number; items_verified: number; items_published: number; detail: string; created_at: string; }

// Full Supabase User type so metadata (full_name, name) is retained
export type AuthUser = User;

// ============================================
// CLIENT SETUP — single instance, created once, used everywhere.
// ============================================

// Backend (Flask on Render). Set VITE_API_URL in .env to point at a different server.
export const API_URL = ((import.meta.env.VITE_API_URL as string | undefined) || 'https://four04-news.onrender.com').replace(/\/+$/, '');

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const supabase: SupabaseClient = createClient(supabaseUrl || '', supabaseAnonKey || '');

function db(): SupabaseClient | null {
  if (!supabaseUrl || !supabaseAnonKey) return null;
  return supabase;
}

// ============================================
// AUTH FUNCTIONS
// ============================================

export async function getCurrentUser(): Promise<AuthUser | null> {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.user ?? null;
}

export function onAuthChange(callback: (user: AuthUser | null) => void) {
  const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
    callback(session?.user ?? null);
  });

  return () => subscription.unsubscribe();
}

export async function signUpWithEmail(email: string, password: string, fullName?: string): Promise<{ error: string | null }> {
  const c = db();
  if (!c) return { error: 'Supabase not configured' };
  const { error } = await c.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName || '',
      },
    },
  });
  return { error: error?.message ?? null };
}

export async function signInWithEmail(email: string, password: string): Promise<{ error: string | null }> {
  const c = db();
  if (!c) return { error: 'Supabase not configured' };
  const { error } = await c.auth.signInWithPassword({ email, password });
  return { error: error?.message ?? null };
}

export async function signInWithGoogle(): Promise<{ error: string | null }> {
  const c = db();
  if (!c) return { error: 'Supabase not configured' };
  const { error } = await c.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.origin },
  });
  return { error: error?.message ?? null };
}

export async function signOut(): Promise<void> {
  await supabase.auth.signOut();
}

// ============================================
// DATA FUNCTIONS (USER SCOPED)
// ============================================

export async function fetchArticles(category: string = 'tech', ignoreCutoff: boolean = false) {
  try {
    let query = supabase.from('articles').select('*');

    // Only apply the 14-day limit if NOT fetching Archive
    if (!ignoreCutoff) {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - 14);
      query = query.gte('created_at', cutoffDate.toISOString());
    }

    query = query.order('created_at', { ascending: false }).limit(100);

    if (category && category.toLowerCase() !== 'all') {
      query = query.eq('category', category);
    }

    const { data, error } = await query;
    if (error) {
      console.error('Error fetching articles:', error);
      return fallbackArticles;
    }

    return (data as Article[]) || [];
  } catch {
    return fallbackArticles;
  }
}

export async function fetchBookmarks(): Promise<Bookmark[]> {
  const c = db(); if (!c) return [];
  try {
    const user = await getCurrentUser();
    if (!user) return [];

    const { data, error } = await c
      .from('bookmarks')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false });

    if (error) throw error;
    return (data ?? []) as Bookmark[];
  } catch { return []; }
}

export async function toggleBookmark(article: Article, isBookmarked: boolean): Promise<void> {
  const c = db(); if (!c) return;
  try {
    const user = await getCurrentUser();
    if (!user) return;

    if (isBookmarked) {
      await c
        .from('bookmarks')
        .delete()
        .eq('article_id', article.id)
        .eq('user_id', user.id);
    } else {
      await c.from('bookmarks').insert({
        article_id: article.id,
        title: article.title,
        user_id: user.id
      });
    }
  } catch {}
}

export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const c = db(); if (!c) return [];
  try {
    const user = await getCurrentUser();
    if (!user) return [];

    const { data } = await c
      .from('chat_history')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: true })
      .limit(20);

    return (data ?? []) as ChatMessage[];
  } catch { return []; }
}

export async function saveChatMessage(role: 'user' | 'assistant', content: string, sources: Article[] | null = null): Promise<void> {
  const c = db(); if (!c) return;
  try {
    const user = await getCurrentUser();
    if (!user) return;

    await c.from('chat_history').insert({
      role,
      content,
      sources,
      user_id: user.id
    });
  } catch {}
}

export async function clearChatHistory(): Promise<void> {
  const c = db(); if (!c) return;
  try {
    const user = await getCurrentUser();
    if (!user) return;

    await c.from('chat_history').delete().eq('user_id', user.id);
  } catch {}
}

export async function fetchAgentRuns(): Promise<AgentRun[]> {
  const c = db(); if (!c) return fallbackAgentRuns as AgentRun[];
  try {
    const { data } = await c.from('agent_runs').select('*').order('created_at', { ascending: false }).limit(10);
    return ((data?.length ? data : fallbackAgentRuns) as AgentRun[]);
  } catch { return fallbackAgentRuns as AgentRun[]; }
}

export async function runPipeline(): Promise<AgentRun[]> {
  const c = db();
  if (!c) return fallbackAgentRuns as AgentRun[];
 
  try {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;
 
    const res = await fetch(`${API_URL}/run-pipeline`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
 
    const result = await res.json();
 
    await c.from('agent_runs').insert([
      {
        agent_name: 'pipeline',
        status: res.ok ? 'completed' : 'error',
        items_processed: result.inserted ?? 0,
        items_verified: result.inserted ?? 0,
        items_published: result.inserted ?? 0,
        detail: result.message || result.error || 'Pipeline run finished.',
        created_at: new Date().toISOString(),
      },
    ]);
  } catch (err) {
    console.error('Pipeline run failed:', err);
  }
 
  return fetchAgentRuns();
}

export async function streamChat(
  messages: { role: 'user' | 'assistant' | 'system'; content: string }[],
  contextArticles: Article[],
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
  onEvent?: (event: ChatEvent) => void
): Promise<void> {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    const res = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        messages,
        articles: contextArticles.slice(0, 5).map((a) => ({
          title: a.title,
          summary: a.summary,
          source: a.source
        })),
        stream: true
      }),
    });

    if (res.status === 401) { onError('Please sign in again to use 404 AI.'); return; }
    if (res.status === 429) { onError('You are sending messages too fast. Try again in a few minutes.'); return; }
    if (!res.ok || !res.body) throw new Error(`bad response ${res.status}`);

    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop() ?? '';

      for (const line of lines) {
        const t = line.trim();
        if (!t.startsWith('data: ')) continue;
        const p = t.slice(6);

        if (p === '[DONE]') {
          onDone();
          return;
        }

        try {
          const parsed = JSON.parse(p);
          if (parsed.event === 'tool') { onEvent?.(parsed as ChatEvent); continue; }
          const tok = parsed.choices?.[0]?.delta?.content || parsed.content || '';
          if (tok) onToken(tok);
        } catch {
          if (p) onToken(p);
        }
      }
    }
    onDone();
  } catch (err) {
    console.error('Chat error:', err);
    onError("I couldn't reach the server. It may be waking up, so try again in a few seconds.");
  }
}

// ============================================
// TOPICS ("keep me in the loop")
// ============================================

export const MAX_TOPICS = 10;

/** Must match slugify() in backend/topics.py. */
export function slugifyTopic(raw: string): string {
  return raw
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60)
    .replace(/-+$/, '');
}

export async function fetchTopics(): Promise<Topic[]> {
  const c = db(); if (!c) return [];
  try {
    const { data, error } = await c.from('topic_subscriptions').select('*').order('created_at', { ascending: false });
    if (error) throw error;
    return (data ?? []) as Topic[];
  } catch (err) { console.error('fetchTopics failed:', err); return []; }
}

/** Latest digest per topic slug. */
export async function fetchLatestDigests(slugs: string[]): Promise<Record<string, Digest>> {
  const c = db(); if (!c || slugs.length === 0) return {};
  try {
    const { data } = await c.from('topic_digests').select('*').in('slug', slugs)
      .order('created_at', { ascending: false }).limit(slugs.length * 3);
    const latest: Record<string, Digest> = {};
    for (const d of (data ?? []) as Digest[]) if (!latest[d.slug]) latest[d.slug] = d;
    return latest;
  } catch { return {}; }
}

/** Newest stories per topic, grouped by slug. */
export async function fetchTopicArticles(slugs: string[], perTopic = 8): Promise<Record<string, Article[]>> {
  const c = db(); if (!c || slugs.length === 0) return {};
  try {
    const { data } = await c.from('articles').select('*')
      .in('category', slugs.map((s) => `topic-${s}`))
      .order('created_at', { ascending: false }).limit(slugs.length * perTopic * 2);
    const grouped: Record<string, Article[]> = {};
    for (const a of (data ?? []) as Article[]) {
      const slug = (a.category ?? '').replace(/^topic-/, '');
      (grouped[slug] ||= []);
      if (grouped[slug].length < perTopic) grouped[slug].push(a);
    }
    return grouped;
  } catch { return {}; }
}

export async function followTopic(raw: string): Promise<{ error: string | null; slug?: string }> {
  const c = db(); if (!c) return { error: 'Supabase not configured' };
  const topic = raw.trim().replace(/\s+/g, ' ');
  const slug = slugifyTopic(topic);
  if (topic.length < 2) return { error: 'Type a topic, for example "quantum computing".' };
  if (topic.length > 60) return { error: 'Keep the topic under 60 characters.' };
  if (!slug) return { error: 'The topic needs some letters or numbers.' };
  const user = await getCurrentUser();
  if (!user) return { error: 'Please sign in first.' };
  const { error } = await c.from('topic_subscriptions').insert({ user_id: user.id, topic, slug, query: topic });
  if (error) {
    if (error.code === '23505') return { error: 'You already follow that topic.' };
    if (/limit/i.test(error.message)) return { error: `You can follow up to ${MAX_TOPICS} topics. Unfollow one first.` };
    return { error: error.message };
  }
  return { error: null, slug };
}

export async function unfollowTopic(slug: string): Promise<{ error: string | null }> {
  const c = db(); if (!c) return { error: 'Supabase not configured' };
  const user = await getCurrentUser();
  if (!user) return { error: 'Please sign in first.' };
  const { error } = await c.from('topic_subscriptions').delete().eq('user_id', user.id).eq('slug', slug);
  return { error: error?.message ?? null };
}

/** Asks the backend to fetch fresh stories and write a new digest for one followed topic. */
export async function refreshTopic(slug: string): Promise<{ error: string | null; newStories?: number }> {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;
    const res = await fetch(`${API_URL}/topics/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({ slug }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) return { error: body.error || 'Could not refresh right now.' };
    return { error: null, newStories: body.new ?? 0 };
  } catch {
    return { error: 'The server did not respond. It may be waking up, so try again in a few seconds.' };
  }
}

export async function fetchBookmarkedArticles(): Promise<Article[]> {
  const c = db(); if (!c) return [];
  try {
    const user = await getCurrentUser();
    if (!user) return [];

    const { data: bookmarkRows, error: bmError } = await c
      .from('bookmarks')
      .select('article_id')
      .eq('user_id', user.id);

    if (bmError || !bookmarkRows || bookmarkRows.length === 0) return [];

    const articleIds = bookmarkRows.map((b) => b.article_id);

    const { data: articles, error: artError } = await c
      .from('articles')
      .select('*')
      .in('id', articleIds);

    if (artError || !articles) return [];
    return articles as Article[];
  } catch (err) {
    console.error("Error fetching bookmarks:", err);
    return [];
  }
}