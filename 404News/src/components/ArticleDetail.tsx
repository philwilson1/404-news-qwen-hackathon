import { useState, useRef, useEffect } from 'react';
import { X, CheckCircle2, Eye, Clock, ExternalLink, Send, Sparkles } from 'lucide-react';
import { streamQwenChat, saveChatMessage, type Article } from '../lib/supabase';
import ReactMarkdown from 'react-markdown';

interface DisplayMessage { id: string; role: 'user' | 'assistant'; content: string; }

export default function ArticleDetail({ article, onClose }: {
  article: Article | null;
  onClose: () => void;
}) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [sending, setSending] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (article) {
      setMessages([
        {
          id: 'system-init',
          role: 'assistant',
          content: `Hi! I am PivotAI. I have fully indexed this article. Ask me any specific questions about it!`
        }
      ]);
    }
  }, [article]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!article) return null;

  const handleSend = async () => {
    const query = input.trim();
    if (!query || sending) return;

    setInput('');
    setSending(false);

    const userMsg: DisplayMessage = { id: `u-${Date.now()}`, role: 'user', content: query };
    const assistantId = `a-${Date.now()}`;
    const assistantMsg: DisplayMessage = { id: assistantId, role: 'assistant', content: '' };
    
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setSending(true);

    // Explicitly pass only THIS article as context to the streaming function
    streamQwenChat(
      [{ role: 'user', content: query }],
      [article], 
      (token) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + token } : m))
        );
      },
      async () => {
        const finalContent = await new Promise<string>((resolve) => {
          setMessages((prev) => {
            const msg = prev.find((m) => m.id === assistantId);
            resolve(msg?.content ?? '');
            return prev;
          });
        });
        await saveChatMessage('assistant', finalContent, [article]);
        setSending(false);
      },
      () => {
        setSending(false);
      }
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 flex items-end sm:items-center justify-center animate-fadeIn"
      onClick={onClose}
    >
      <div
        className="bg-zinc-950 border border-zinc-800 rounded-t-2xl sm:rounded-2xl w-full sm:max-w-xl h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-zinc-950 border-b border-zinc-900 px-4 py-3 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2 text-[11px]">
            <span className="flex items-center justify-center w-5 h-5 rounded bg-zinc-800 text-zinc-400 font-bold text-[9px]">
              {article.source_logo}
            </span>
            <span className="text-zinc-400 font-medium">{article.source}</span>
          </div>
          <button onClick={onClose} className="p-1 text-zinc-500 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Content Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar">
          {article.image_url && (
            <div className="h-44 overflow-hidden rounded-xl">
              <img src={article.image_url} alt="" className="w-full h-full object-cover" />
            </div>
          )}

          <div>
            <h2 className="text-white font-bold text-xl leading-tight mb-2">{article.title}</h2>
            <div className="flex items-center gap-3 text-[11px] text-zinc-500 mb-3">
              {article.verified && (
                <span className="inline-flex items-center gap-1 text-emerald-400">
                  <CheckCircle2 size={12} />
                  <span className="font-semibold">Verified · {(article.confidence * 100).toFixed(0)}%</span>
                </span>
              )}
              <span className="inline-flex items-center gap-1"><Eye size={12} /> {article.views}</span>
              <span className="inline-flex items-center gap-1"><Clock size={12} /> {article.read_time} min read</span>
          <div className="text-zinc-300 text-sm leading-relaxed bg-zinc-900/40 p-3 rounded-xl border border-zinc-900 prose prose-invert prose-sm max-w-none">
  <ReactMarkdown>{article.summary}</ReactMarkdown>
</div>

          {/* Inline Contextual Chat */}
          <div className="pt-4 border-t border-zinc-900 flex flex-col flex-1 min-h-[300px]">
            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">
              Context-Aware Discussion Panel
            </p>
            <div className="flex-1 space-y-3 mb-4">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[90%] rounded-xl px-3 py-2 text-xs ${msg.role === 'user' ? 'bg-sky-500 text-white' : 'bg-zinc-900 border border-zinc-800 text-zinc-200'}`}>
                    {msg.role === 'assistant' && (
                      <div className="flex items-center gap-1.5 mb-1 text-sky-400 font-semibold">
                        <Sparkles size={10} /> <span>PivotAI</span>
                      </div>
                    )}
                    <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
          </div>
        </div>

        {/* Fixed Input Box at Bottom of Modal */}
        <div className="p-3 border-t border-zinc-900 bg-zinc-950 flex-shrink-0">
          <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-xl p-1.5">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder={`Ask about this story...`}
              disabled={sending}
              className="flex-1 bg-transparent text-white text-xs placeholder:text-zinc-600 outline-none px-2"
            />
            <button
              onClick={handleSend}
              disabled={sending || !input.trim()}
              className="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center text-white transition-transform disabled:opacity-40"
            >
              <Send size={12} />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}