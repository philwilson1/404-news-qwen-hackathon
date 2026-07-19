import { useState } from 'react';
import { Bookmark, CheckCircle2, TrendingUp, Eye, Clock, ChevronDown } from 'lucide-react';
import type { Article } from '../lib/supabase';

const vibeColors: Record<string, string> = {
  'deep-dives': 'text-sky-400 bg-sky-500/10 border-sky-500/20',
  'hype': 'text-rose-400 bg-rose-500/10 border-rose-500/20',
  'launch-hub': 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
};
const tagColors: Record<string, string> = {
  'Model Release': 'text-sky-400', 'Launch': 'text-emerald-400', 'Drama': 'text-rose-400',
  'Research': 'text-blue-400', 'Funding': 'text-amber-400', 'Hot Take': 'text-rose-400',
  'Viral': 'text-purple-400', 'Analysis': 'text-sky-400',
};

export default function NewsCard({ article, featured = false, isBookmarked = false, onBookmark, onOpen }: {
  article: Article; featured?: boolean; isBookmarked?: boolean;
  onBookmark?: (a: Article, isBookmarked: boolean) => void;
  onOpen?: (a: Article) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [imgError, setImgError] = useState(false);
  return (
    <article
      className={`px-4 py-3 animate-fadeIn cursor-pointer ${featured ? 'mb-2' : 'border-b border-zinc-900'}`}
      onClick={() => onOpen?.(article)}
    >
      {featured && !imgError && (
        <div className="relative rounded-2xl overflow-hidden mb-3 h-56">
          <img src={article.image_url} alt="" className="w-full h-full object-cover" onError={() => setImgError(true)} />
          <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/40 to-transparent" />
          <div className="absolute top-3 left-3 flex items-center gap-2">
            {article.trending && (<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-500 text-white text-[10px] font-bold"><TrendingUp size={10} /> TRENDING</span>)}
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${vibeColors[article.vibe] ?? 'text-sky-400 bg-sky-500/10 border-sky-500/20'}`}>{article.vibe.replace('-', ' ')}</span>
          </div>
        </div>
      )}
      <div className="flex items-center gap-2 mb-2 text-[11px]">
        <span className="flex items-center justify-center w-5 h-5 rounded bg-zinc-800 text-zinc-400 font-bold text-[9px] flex-shrink-0">{article.source_logo}</span>
        <span className="text-zinc-400 font-medium truncate">{article.source}</span>
        <span className="text-zinc-700">·</span>
        <span className="text-zinc-500">{article.published_at}</span>
      </div>
      <h3 className={`text-white font-bold leading-tight mb-1.5 ${featured ? 'text-xl' : 'text-base'}`}>{article.title}</h3>
      <p className={`text-zinc-400 text-sm leading-relaxed ${featured ? '' : 'line-clamp-2'} ${expanded ? 'line-clamp-none' : ''}`}>{article.summary}</p>
      {featured && (
        <button
          onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          className="flex items-center gap-1 text-xs text-sky-400 mt-1.5 font-medium"
        >
          {expanded ? 'Show less' : 'Read more'}
          <ChevronDown size={12} className={`transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </button>
      )}
      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-3 text-[11px] text-zinc-500">
          {article.verified && (<span className="inline-flex items-center gap-1 text-emerald-400"><CheckCircle2 size={12} /><span className="font-semibold">Verified · {(article.confidence * 100).toFixed(0)}%</span></span>)}
          <span className="inline-flex items-center gap-1"><Eye size={12} /> {article.views}</span>
          <span className="inline-flex items-center gap-1"><Clock size={12} /> {article.read_time} min</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold ${tagColors[article.tag] ?? 'text-zinc-500'}`}>{article.tag}</span>
          {onBookmark && (
            <button
              onClick={(e) => { e.stopPropagation(); onBookmark(article, isBookmarked); }}
              className={`p-1 transition-colors ${isBookmarked ? 'text-sky-400' : 'text-zinc-600 hover:text-sky-400'}`}
            >
              <Bookmark size={16} fill={isBookmarked ? 'currentColor' : 'none'} />
            </button>
          )}
        </div>
      </div>
      {featured && article.agent_log && expanded && (
        <div className="mt-3 rounded-xl bg-zinc-900 border border-zinc-800 p-3 space-y-1.5">
          <p className="text-[10px] font-bold text-zinc-600 uppercase tracking-wider mb-1">Agent Pipeline</p>
          {article.agent_log.map((log, i) => (<div key={i} className="flex items-center gap-2 text-[11px]"><CheckCircle2 size={11} className="text-emerald-400 flex-shrink-0" /><span className="font-semibold text-white capitalize">{log.agent}</span><span className="text-zinc-500 truncate">{log.detail}</span></div>))}
        </div>
      )}
    </article>
  );
}