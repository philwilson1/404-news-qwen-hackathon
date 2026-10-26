import { useState, useEffect, useRef, useCallback } from 'react';
import { Sparkles, Send, BellRing, Newspaper, ListChecks, TrendingUp, Trash2, Cpu, Check, ShieldCheck } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { fetchArticles, fetchChatHistory, saveChatMessage, clearChatHistory, streamChat, type Article, type ChatMessage, type ChatEvent } from '../lib/supabase';
import AgentPipeline from './AgentPipeline';

interface DisplayMessage { id: string; role: 'user' | 'assistant'; content: string; sources?: Article[]; streaming?: boolean; actions?: string[]; }
const suggestions = [
  { icon: BellRing, text: 'Keep me in the loop on cybersecurity', color: 'text-sky-400 bg-sky-500/10 border-sky-500/20' },
  { icon: Newspaper, text: "What's new in Nigerian fintech?", color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
  { icon: TrendingUp, text: 'Follow quantum computing for me', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
  { icon: ShieldCheck, text: 'Is this real? ', label: 'Check a WhatsApp forward or rumour', prefill: true, color: 'text-violet-400 bg-violet-500/10 border-violet-500/20' },
  { icon: ListChecks, text: 'What topics am I following?', color: 'text-rose-400 bg-rose-500/10 border-rose-500/20' },
];

export default function AIView() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [pipelineActive, setPipelineActive] = useState(false);
  const [pipelineKey, setPipelineKey] = useState(0);
  const pendingStreamRef = useRef<(() => void) | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const loadContext = useCallback(async () => {
    try { const [articleData, chatData] = await Promise.all([fetchArticles(), fetchChatHistory()]); setArticles(articleData); setMessages(chatData.map((m: ChatMessage) => ({ id: m.id, role: m.role, content: m.content, sources: m.sources ?? undefined }))); } catch {}
    setLoading(false);
  }, []);
  useEffect(() => { loadContext(); }, [loadContext]);
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }); }, [messages, pipelineActive]);

  const startStreaming = useCallback((history: { role: 'user' | 'assistant'; content: string }[], assistantId: string, topArticles: Article[]) => {
    const patch = (fn: (m: DisplayMessage) => DisplayMessage) =>
      setMessages((prev) => prev.map((m) => m.id === assistantId ? fn(m) : m));
    streamChat(history, topArticles,
      (token: string) => patch((m) => ({ ...m, content: m.content + token })),
      async () => {
        patch((m) => ({ ...m, streaming: false }));
        const finalContent = await new Promise<string>((resolve) => {
          setMessages((prev) => { const msg = prev.find((m) => m.id === assistantId); resolve(msg?.content ?? ''); return prev; });
        });
        if (finalContent) await saveChatMessage('assistant', finalContent, topArticles);
        setSending(false);
      },
      (err: string) => { patch((m) => ({ ...m, streaming: false, content: m.content ? `${m.content}\n\n${err}` : err })); setSending(false); },
      (ev: ChatEvent) => {
        if (ev.status !== 'done' || !ev.changed || !ev.topic) return;
        const label = ev.name === 'unfollow_topic' ? `Unfollowed ${ev.topic}` : `Following ${ev.topic}`;
        patch((m) => ({ ...m, actions: [...(m.actions ?? []), label] }));
      }
    );
  }, []);

  const handlePipelineComplete = useCallback(() => {
    setPipelineActive(false);
    const stream = pendingStreamRef.current;
    if (stream) { pendingStreamRef.current = null; stream(); }
  }, []);

  const handleSend = async (text?: string) => {
    const query = (text ?? input).trim(); if (!query || sending) return; setInput(''); setSending(true);
    const userMsg: DisplayMessage = { id: `u-${Date.now()}`, role: 'user', content: query };
    const assistantId = `a-${Date.now()}`;
    const assistantMsg: DisplayMessage = { id: assistantId, role: 'assistant', content: '', streaming: true };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    await saveChatMessage('user', query);
    const topArticles = articles.slice(0, 5);
    const history = [
      ...messages.filter((m) => m.content && !m.streaming).slice(-6).map((m) => ({ role: m.role, content: m.content })),
      { role: 'user' as const, content: query },
    ];

    pendingStreamRef.current = () => startStreaming(history, assistantId, topArticles);
    setPipelineKey((k) => k + 1);
    setPipelineActive(true);
  };

  const handleClear = async () => { await clearChatHistory(); setMessages([]); };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] w-full text-zinc-200 px-4">

      {/* Scrollable Message Container */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto no-scrollbar pt-4 pb-4">
        <div className="text-center mb-6 flex-shrink-0">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-sky-400 to-blue-600 shadow-lg shadow-sky-500/30 mb-3">
            <Sparkles size={26} className="text-white" />
          </div>
          <h2 className="text-white font-bold text-xl">404 AI</h2>
          <div className="flex items-center justify-center gap-2 mt-1">
            <p className="text-zinc-500 text-sm">Ask about the news, or tell me what to keep you posted on</p>
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-sky-500/10 border border-sky-500/20">
              <Cpu size={9} className="text-sky-400" />
              <span className="text-[9px] font-bold text-sky-400">GROQ</span>
            </span>
          </div>
        </div>

        {pipelineActive && <AgentPipeline key={pipelineKey} active={pipelineActive} onComplete={handlePipelineComplete} />}

        {messages.length === 0 && !loading && !pipelineActive ? (
          <div className="space-y-2 max-w-2xl mx-auto">
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-2">Try asking</p>
            {suggestions.map((s, i) => {
              const Icon = s.icon;
              return (
                <button key={i} onClick={() => (s.prefill ? setInput(s.text) : handleSend(s.text))} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border text-left text-sm font-medium text-zinc-300 transition-all hover:scale-[1.01] ${s.color}`}>
                  <Icon size={16} />{s.label ?? s.text}
                </button>
              );
            })}
          </div>
        ) : (
          <div className="space-y-4 max-w-2xl mx-auto">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${msg.role === 'user' ? 'bg-sky-500 text-white' : 'bg-zinc-900 border border-zinc-800 text-zinc-200'}`}>
                  {msg.role === 'assistant' && (
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className="w-5 h-5 rounded-lg bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center">
                        <Sparkles size={10} className="text-white" />
                      </div>
                      <span className="text-[11px] font-semibold text-sky-400">404 AI</span>
                    </div>
                  )}
                  <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown
                      components={{
                        a: ({ node: _node, ...props }) => (
                          <a {...props} target="_blank" rel="noopener noreferrer" className="text-sky-400 underline break-words" />
                        ),
                      }}
                    >{msg.content}</ReactMarkdown>
                    {msg.streaming && pipelineActive === false && (
                      <span className="inline-block w-1.5 h-4 bg-sky-400 ml-0.5 animate-pulse align-middle" />
                    )}
                  </div>
                  {msg.actions && msg.actions.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {msg.actions.map((a, i) => (
                        <span key={i} className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-1 rounded-full">
                          <Check size={11} />{a}
                        </span>
                      ))}
                    </div>
                  )}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-zinc-800">
                      <p className="text-[10px] font-semibold text-zinc-500 uppercase mb-1">Sources</p>
                      <div className="flex flex-wrap gap-1">
                        {msg.sources.map((s, i) => (
                          <span key={i} className="text-[10px] text-zinc-400 bg-zinc-800 px-1.5 py-0.5 rounded">{s.source}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Floating Bottom Input Area */}
      <div className="flex flex-col items-center pt-2 pb-6 flex-shrink-0 bg-transparent">
        {messages.length > 0 && (
          <button onClick={handleClear} className="flex items-center gap-1 text-xs text-zinc-600 hover:text-rose-400 transition-colors mb-3">
            <Trash2 size={11} />Clear conversation
          </button>
        )}
        <div className="w-full max-w-2xl flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-2xl p-2 shadow-2xl">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask, or say &quot;keep me posted on...&quot;"
            disabled={sending}
            className="flex-1 bg-transparent text-white text-sm placeholder:text-zinc-600 outline-none px-2 disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={sending || !input.trim()}
            className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-sky-500/30 hover:scale-105 transition-transform disabled:opacity-40 disabled:hover:scale-100"
          >
            <Send size={15} />
          </button>
        </div>
      </div>

    </div>
  );
}