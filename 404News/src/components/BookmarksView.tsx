import { useState, useEffect, useCallback } from 'react';
import { ArrowLeft, Bookmark as BookmarkIcon, Loader2 } from 'lucide-react';
import { fetchBookmarkedArticles, toggleBookmark, type Article } from '../lib/supabase';
import NewsCard from './NewsCard';
import ArticleDetail from './ArticleDetail';

export default function BookmarksView({ onBack }: { onBack: () => void }) {
  const [bookmarks, setBookmarks] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const articles = await fetchBookmarkedArticles();
      setBookmarks(articles);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  // Every bookmark shown here is, by definition, already bookmarked —
  // so tapping the bookmark icon here always means "remove."
  const handleBookmarkToggle = async (article: Article, _isBookmarked: boolean) => {
    setBookmarks((prev) => prev.filter((item) => item.id !== article.id));
    await toggleBookmark(article, true);
  };

  return (
    <div className="pt-2 pb-24 min-h-screen">
      <div className="px-4 mb-4 flex items-center gap-3">
        <button onClick={onBack} className="p-1 text-zinc-400 hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </button>
        <div>
          <h2 className="text-white font-bold text-lg leading-tight">Bookmarks</h2>
          <p className="text-xs text-zinc-500">{bookmarks.length} saved {bookmarks.length === 1 ? 'story' : 'stories'}</p>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-16 text-zinc-500 gap-2 text-sm">
          <Loader2 size={16} className="animate-spin" />
          Loading bookmarks...
        </div>
      )}

      {!loading && bookmarks.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center px-4">
          <BookmarkIcon size={32} className="text-zinc-600 mb-3" />
          <p className="text-white font-semibold">No bookmarks yet</p>
          <p className="text-zinc-500 text-sm mt-1">Tap the bookmark icon on any story to save it here.</p>
        </div>
      )}

      {!loading && bookmarks.length > 0 && (
        <div className="space-y-0.5">
          {bookmarks.map((article) => (
            <NewsCard
              key={article.id}
              article={article}
              isBookmarked={true}
              onBookmark={handleBookmarkToggle}
              onOpen={setSelectedArticle}
            />
          ))}
        </div>
      )}

      <ArticleDetail article={selectedArticle} onClose={() => setSelectedArticle(null)} />
    </div>
  );
}