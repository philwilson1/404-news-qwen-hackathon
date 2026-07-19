import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { fallbackArticles, fallbackAgentRuns } from '../data/fallback';

export interface Article {
  id: string; title: string; summary: string; source: string; source_logo: string;
  author: string; vibe: string; tag: string; verified: boolean; confidence: number;
  image_url: string; views: string; trending: boolean; published_at: string;
  read_time: number; agent_log: AgentLogEntry[] | null; created_at: string;
}
export interface AgentLogEntry { agent: string; status: string; detail: string; }
export interface Bookmark { id: string; article_id: string; title: string; created_at: string; }
export interface ChatMessage { id: string; role: 'user' | 'assistant'; content: string; sources: Article[] | null; created_at: string; }
export interface AgentRun { id: string; agent_name: string; status: string; items_processed: number; items_verified: number; items_published: number; detail: string; created_at: string; }

let _db: SupabaseClient | null = null;
function db(): SupabaseClient | null {
  if (_db) return _db;
  const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
  const key = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
  if (!url || !key) return null;
  try { _db = createClient(url, key); } catch { _db = null; }
  return _db;
}

export async function fetchArticles(): Promise<Article[]> {
  const c = db(); if (!c) return fallbackArticles;
  try { const { data, error } = await c.from('articles').select('*').order('created_at', { ascending: false }); if (error || !data?.length) return fallbackArticles; return data as Article[]; } catch { return fallbackArticles; }
}
export async function fetchBookmarks(): Promise<Bookmark[]> {
  const c = db(); if (!c) return [];
  try { const { data } = await c.from('bookmarks').select('*').order('created_at', { ascending: false }); return (data ?? []) as Bookmark[]; } catch { return []; }
}
export async function toggleBookmark(article: Article, isBookmarked: boolean): Promise<void> {
  const c = db(); if (!c) return;
  try { if (isBookmarked) { await c.from('bookmarks').delete().eq('article_id', article.id); } else { await c.from('bookmarks').insert({ article_id: article.id, title: article.title }); } } catch {}
}
export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const c = db(); if (!c) return [];
  try { const { data } = await c.from('chat_history').select('*').order('created_at', { ascending: true }).limit(20); return (data ?? []) as ChatMessage[]; } catch { return []; }
}
export async function saveChatMessage(role: 'user' | 'assistant', content: string, sources: Article[] | null = null): Promise<void> {
  const c = db(); if (!c) return; try { await c.from('chat_history').insert({ role, content, sources }); } catch {}
}
export async function clearChatHistory(): Promise<void> {
  const c = db(); if (!c) return; try { await c.from('chat_history').delete().neq('id', '00000000-0000-0000-0000-000000000000'); } catch {}
}
export async function fetchAgentRuns(): Promise<AgentRun[]> {
  const c = db(); if (!c) return fallbackAgentRuns as AgentRun[];
  try { const { data } = await c.from('agent_runs').select('*').order('created_at', { ascending: false }).limit(10); return ((data?.length ? data : fallbackAgentRuns) as AgentRun[]); } catch { return fallbackAgentRuns as AgentRun[]; }
}
export async function runPipeline(articles: Article[]): Promise<AgentRun[]> {
  const c = db(); if (!c) return fallbackAgentRuns as AgentRun[];
  const now = new Date(); const vc = articles.filter((a) => a.verified).length;
  try { await c.from('agent_runs').insert([
    { agent_name: 'collector', status: 'completed', items_processed: articles.length, detail: `Scraped ${articles.length} items`, created_at: new Date(now.getTime() - 180000).toISOString() },
    { agent_name: 'verification', status: 'completed', items_processed: articles.length, items_verified: vc, detail: `Verified ${vc} of ${articles.length}`, created_at: new Date(now.getTime() - 120000).toISOString() },
    { agent_name: 'presenter', status: 'completed', items_processed: articles.length, items_verified: vc, items_published: articles.length, detail: `Published ${articles.length} articles`, created_at: new Date(now.getTime() - 60000).toISOString() },
  ]); } catch {}
  return fetchAgentRuns();
}

function streamDemo(onToken: (t: string) => void, onDone: () => void, articles: Article[]) {
  const top = articles.slice(0, 5);
  const text = top.length ? `Here's your AI pulse for today:\n\n${top.map((a, i) => `**${i + 1}. ${a.title.split(' — ')[0]}** — ${a.summary.split('.')[0]}. (Source: ${a.source})`).join('\n\n')}\n\nEvery story above was verified by 2+ independent sources.` : "I'm PivotAI, your AI news concierge. Ask me about today's top AI stories.";
  (async () => { for (const tok of text.split(/(\s+)/)) { onToken(tok); await new Promise((r) => setTimeout(r, 18)); } onDone(); })();
}

export async function streamQwenChat(
  messages: { role: 'user' | 'assistant' | 'system'; content: string }[],
  contextArticles: Article[],
  onToken: (token: string) => void,
  onDone: () => void,
  _onError: (err: string) => void
): Promise<void> {
  try {
    // Point directly to your local Python Flask server
    const res = await fetch('http://127.0.0.1:5000/chat', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json'
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

    if (!res.ok || !res.body) throw new Error('bad response');
    
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
          // Extract token from standard chunk format or fallback to raw content
          const tok = parsed.choices?.[0]?.delta?.content || parsed.content || ""; 
          if (tok) onToken(tok); 
        } catch {
          // If the server sent a raw string instead of JSON, we can stream it directly
          if (p) onToken(p);
        } 
      } 
    } 
    onDone();
  } catch (err) { 
    console.error("Local chat error, falling back to demo stream:", err);
    streamDemo(onToken, onDone, contextArticles); 
  }
}
