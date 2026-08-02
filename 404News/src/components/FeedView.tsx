import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { fetchArticles, fetchBookmarks, toggleBookmark, runPipeline, type Article } from '../lib/supabase';
import { categories } from '../data/fallback';
import NewsCard from './NewsCard';
import ArticleDetail from './ArticleDetail';

interface FeedViewProps {
  category?: string;
}

export default function FeedView({ category = 'tech' }: FeedViewProps) {
  const [activeVibe, setActiveVibe] = useState<string>('all');
  const [timeFilter, setTimeFilter] = useState<'all' | 'today' | 'yesterday' | 'archive'>('all');
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { 
      // If timeFilter is 'archive', bypass the 14-day cutoff on fetch
      const ignoreCutoff = timeFilter === 'archive';
      const [data, bookmarks] = await Promise.all([
        fetchArticles(category, ignoreCutoff), 
        fetchBookmarks()
      ]); 
      setArticles(data || []); 
      setBookmarkedIds(new Set(bookmarks.map((b) => b.article_id))); 
    } catch {}
    setLoading(false);
  }, [category, timeFilter]);

  useEffect(() => { 
    load(); 
  }, [load]);

  const handleRefresh = async () => { 
    if (pipelineRunning || articles.length === 0) return; 
    setPipelineRunning(true); 
    try { 
      await runPipeline(); 
      await load(); 
    } catch {} 
    setTimeout(() => setPipelineRunning(false), 1500); 
  };

  const handleBookmark = async (article: Article, isBookmarked: boolean) => {
    await toggleBookmark(article, isBookmarked);
    setBookmarkedIds((prev) => { 
      const next = new Set(prev); 
      if (isBookmarked) next.delete(article.id); 
      else next.add(article.id); 
      return next; 
    });
  };

  // 1. Filter by Vibe first
  const vibeFiltered = activeVibe === 'all' ? articles : articles.filter((a) => a.vibe === activeVibe);

  // 2. Filter by Time (Today / Yesterday / All / Archive)
  const filtered = vibeFiltered.filter((article) => {
    if (timeFilter === 'all') return true;

    const articleDate = new Date(article.created_at);
    const today = new Date();
    
    const isToday = articleDate.toDateString() === today.toDateString();

    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    const isYesterday = articleDate.toDateString() === yesterday.toDateString();

    if (timeFilter === 'today') return isToday;
    if (timeFilter === 'yesterday') return isYesterday;
    
    // Archive: Display articles older than 14 days
    if (timeFilter === 'archive') {
      const fourteenDaysAgo = new Date();
      fourteenDaysAgo.setDate(today.getDate() - 14);
      return articleDate < fourteenDaysAgo;
    }

    return true;
  });

  const featured = filtered[0]; 
  const rest = filtered.slice(1);

  if (loading) return (
    <div className="pt-2 pb-24">
      <div className="px-4 mb-3"><div className="h-8 w-48 rounded-lg bg-zinc-900 animate-pulse" /></div>
      <div className="mx-4 mb-4 rounded-2xl bg-zinc-900 h-64 animate-pulse" />
      <div className="space-y-3 px-4">{[1, 2, 3].map((i) => (<div key={i} className="flex gap-3"><div className="w-20 h-20 rounded-xl bg-zinc-900 animate-pulse" /><div className="flex-1 space-y-2"><div className="h-3 w-16 rounded bg-zinc-900 animate-pulse" /><div className="h-4 rounded bg-zinc-900 animate-pulse" /><div className="h-3 w-24 rounded bg-zinc-900 animate-pulse" /></div></div>))}</div>
    </div>
  );

  if (articles.length === 0) return (
    <div className="pt-2 pb-24 px-4">
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <AlertCircle size={32} className="text-zinc-600 mb-3" />
        <p className="text-white font-semibold">Couldn't load the feed for {category}</p>
        <p className="text-zinc-500 text-sm mt-1 mb-4">Our agents are scanning sources — check back soon or run the scraper.</p>
        <button onClick={load} className="px-4 py-2 rounded-xl bg-zinc-900 border border-zinc-800 text-white text-sm font-semibold hover:bg-zinc-800 transition-colors">Retry</button>
      </div>
    </div>
  );

  return (
    <div className="pt-2 pb-24">
      <div className="px-4 mb-3">
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
          <button onClick={() => setActiveVibe('all')} className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${activeVibe === 'all' ? 'bg-sky-500 text-white border-sky-500' : 'bg-zinc-900 text-zinc-400 border-zinc-800'}`}>All News</button>
          {categories.map((cat) => (<button key={cat.id} onClick={() => setActiveVibe(cat.id)} className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${activeVibe === cat.id ? 'bg-sky-500 text-white border-sky-500' : 'bg-zinc-900 text-zinc-400 border-zinc-800'}`}>{cat.label}</button>))}
        </div>
      </div>

      <div className="px-4 mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-white font-bold text-lg leading-tight">
            {timeFilter === 'archive' ? 'Archived News' : "Today's Pulse"}
          </h2>
          <p className="text-xs text-zinc-500">{filtered.length} verified stories</p>
        </div>

        {/* Top-Right Area: Time Filter Toggle & Run Pipeline */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 rounded-lg p-1 text-[11px]">
            <button
              onClick={() => setTimeFilter('all')}
              className={`px-2 py-0.5 rounded transition-colors ${timeFilter === 'all' ? 'bg-sky-500 text-white font-semibold' : 'text-zinc-400 hover:text-white'}`}
            >
              All
            </button>
            <button
              onClick={() => setTimeFilter('today')}
              className={`px-2 py-0.5 rounded transition-colors ${timeFilter === 'today' ? 'bg-sky-500 text-white font-semibold' : 'text-zinc-400 hover:text-white'}`}
            >
              Today
            </button>
            <button
              onClick={() => setTimeFilter('yesterday')}
              className={`px-2 py-0.5 rounded transition-colors ${timeFilter === 'yesterday' ? 'bg-sky-500 text-white font-semibold' : 'text-zinc-400 hover:text-white'}`}
            >
              Yesterday
            </button>
            <button
              onClick={() => setTimeFilter('archive')}
              className={`px-2 py-0.5 rounded transition-colors ${timeFilter === 'archive' ? 'bg-amber-500 text-white font-semibold' : 'text-zinc-400 hover:text-white'}`}
            >
              Archive
            </button>
          </div>

          <button onClick={handleRefresh} disabled={pipelineRunning} className="flex items-center gap-1 text-xs font-medium text-sky-400 disabled:text-zinc-600">
            <RefreshCw size={12} className={pipelineRunning ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {pipelineRunning && (
        <div className="mx-4 mb-3 rounded-xl bg-zinc-900 border border-zinc-800 p-3 animate-fadeIn">
          <div className="flex items-center gap-2 mb-2"><span className="flex h-2 w-2 relative"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" /><span className="relative inline-flex rounded-full h-2 w-2 bg-sky-400" /></span><p className="text-xs font-semibold text-sky-400">Multi-agent pipeline active</p></div>
          <div className="space-y-1.5">{[{ n: 'Collector', d: 'Scraping sources...' }, { n: 'Verification', d: 'Cross-checking sources...' }, { n: 'Presenter', d: 'Writing hooks...' }].map((a, i) => (<div key={i} className="flex items-center gap-2 text-xs text-zinc-500"><div className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" style={{ animationDelay: `${i * 200}ms` }} /><span className="font-medium text-white">{a.n}</span><span className="text-zinc-600">{a.d}</span></div>))}</div>
        </div>
      )}

      {featured && <NewsCard article={featured} featured isBookmarked={bookmarkedIds.has(featured.id)} onBookmark={handleBookmark} onOpen={setSelectedArticle} />}
      <div className="space-y-0.5">{rest.map((article) => <NewsCard key={article.id} article={article} isBookmarked={bookmarkedIds.has(article.id)} onBookmark={handleBookmark} onOpen={setSelectedArticle} />)}</div>
      
      {filtered.length === 0 && (
        <div className="text-center py-20 px-4">
          <p className="text-white font-semibold">No stories found for this filter</p>
          <p className="text-zinc-500 text-sm mt-1">Try switching to "All" or check back later.</p>
        </div>
      )}

      <ArticleDetail article={selectedArticle} onClose={() => setSelectedArticle(null)} />
    </div>
  );
}