import { useState, useEffect, useRef, useCallback } from 'react';
import { Sparkles, Send, TrendingUp, FileText, Zap, ShieldCheck, Trash2, Cpu } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { fetchArticles, fetchChatHistory, saveChatMessage, clearChatHistory, streamQwenChat, type Article, type ChatMessage } from '../lib/supabase';
import AgentPipeline from './AgentPipeline';

interface DisplayMessage { id: string; role: 'user' | 'assistant'; content: string; sources?: Article[]; streaming?: boolean; }
const suggestions = [
  { icon: TrendingUp, text: "What's trending in AI right now?", color: 'text-rose-400 bg-rose-500/10 border-rose-500/20' },
  { icon: FileText, text: 'Summarize the GPT-5 paper in 3 points', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  { icon: Zap, text: 'Explain Magistral vs o3 in simple terms', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
  { icon: ShieldCheck, text: 'Is the AlphaFold 3 hype real?', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
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

  const startStreaming = useCallback((query: string, assistantId: string, topArticles: Article[]) => {
    streamQwenChat([{ role: 'user', content: query }], topArticles,
      (token) => setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, content: m.content + token } : m)),
      async () => {
        setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, streaming: false } : m));
        const finalContent = await new Promise<string>((resolve) => {
          setMessages((prev) => { const msg = prev.find((m) => m.id === assistantId); resolve(msg?.content ?? ''); return prev; });
        });
        await saveChatMessage('assistant', finalContent, topArticles);
        setSending(false);
      },
      () => { setSending(false); }
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

    pendingStreamRef.current = () => startStreaming(query, assistantId, topArticles);
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
            <p className="text-zinc-500 text-sm">Ask me anything about today's AI news</p>
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-sky-500/10 border border-sky-500/20">
              <Cpu size={9} className="text-sky-400" />
              <span className="text-[9px] font-bold text-sky-400">QWEN</span>
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
                <button key={i} onClick={() => handleSend(s.text)} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border text-left text-sm font-medium text-zinc-300 transition-all hover:scale-[1.01] ${s.color}`}>
                  <Icon size={16} />{s.text}
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
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                    {msg.streaming && pipelineActive === false && (
                      <span className="inline-block w-1.5 h-4 bg-sky-400 ml-0.5 animate-pulse align-middle" />
                    )}
                  </div>
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
            placeholder="Ask about any AI story..."
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