import { useState, useCallback } from 'react';
import { ArrowLeft, Search as SearchIcon, X } from 'lucide-react';
import { supabase, toggleBookmark, type Article } from '../lib/supabase';
import NewsCard from './NewsCard';
import ArticleDetail from './ArticleDetail';

export default function SearchView({ onBack }: { onBack: () => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Article[]>([]);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  const runSearch = useCallback(async () => {
    const q = query.trim();
    if (!q) return;

    setSearching(true);
    setHasSearched(true);

    try {
      // Matches the search word against title OR summary, case-insensitive
      const { data, error } = await supabase
        .from('articles')
        .select('*')
        .or(`title.ilike.%${q}%,summary.ilike.%${q}%`)
        .order('created_at', { ascending: false })
        .limit(30);

      if (!error && data) {
        setResults(data as Article[]);
      } else {
        setResults([]);
      }
    } catch {
      setResults([]);
    }

    setSearching(false);
  }, [query]);

  const handleBookmark = async (article: Article, isBookmarked: boolean) => {
    await toggleBookmark(article, isBookmarked);
    setBookmarkedIds((prev) => {
      const next = new Set(prev);
      if (isBookmarked) next.delete(article.id);
      else next.add(article.id);
      return next;
    });
  };

  const clearSearch = () => {
    setQuery('');
    setResults([]);
    setHasSearched(false);
  };

  return (
    <div className="pt-2 pb-24 min-h-screen">
      <div className="px-4 mb-4 flex items-center gap-3">
        <button onClick={onBack} className="p-1 text-zinc-400 hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </button>
        <h2 className="text-white font-bold text-lg leading-tight">Search</h2>
      </div>

      <div className="px-4 mb-4">
        <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-xl p-2.5">
          <SearchIcon size={16} className="text-zinc-500 flex-shrink-0" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runSearch()}
            placeholder="Search articles..."
            className="flex-1 bg-transparent text-white text-sm placeholder:text-zinc-600 outline-none"
          />
          {query && (
            <button onClick={clearSearch} className="text-zinc-500 hover:text-white transition-colors">
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {searching && (
        <div className="text-center text-zinc-500 text-sm py-12">Searching...</div>
      )}

      {!searching && hasSearched && results.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center px-4">
          <SearchIcon size={32} className="text-zinc-600 mb-3" />
          <p className="text-white font-semibold">No results for "{query}"</p>
          <p className="text-zinc-500 text-sm mt-1">Try a different word or phrase.</p>
        </div>
      )}

      {!searching && results.length > 0 && (
        <div className="space-y-0.5">
          {results.map((article) => (
            <NewsCard
              key={article.id}
              article={article}
              isBookmarked={bookmarkedIds.has(article.id)}
              onBookmark={handleBookmark}
              onOpen={setSelectedArticle}
            />
          ))}
        </div>
      )}

      <ArticleDetail article={selectedArticle} onClose={() => setSelectedArticle(null)} />
    </div>
  );
}