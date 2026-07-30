import { useState, useCallback, useEffect } from 'react';
import Header from './components/Header';
import BottomNav, { type Tab } from './components/BottomNav';
import SideDrawer from './components/SideDrawer';
import FeedView from './components/FeedView';
import AIView from './components/AIView';
import ProfileView from './components/ProfileView';
import BookmarksView from './components/BookmarksView';
import Toast, { type ToastState } from './components/Toast';
import AuthView from './components/AuthView';
import { getCurrentUser, onAuthChange, type AuthUser } from './lib/supabase';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('feed');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [showBookmarks, setShowBookmarks] = useState(false);

  useEffect(() => {
    getCurrentUser().then((u) => {
      setUser(u);
      setAuthLoading(false);
    });
    const unsubscribe = onAuthChange((u) => setUser(u));
    return unsubscribe;
  }, []);

  const showLockedToast = useCallback(() => {
    setToast({
      id: Date.now(),
      title: 'Under Construction by the Agents',
      message: 'Our AI team is currently optimizing the data pipelines for this category. Stay tuned — greatness takes a little time.',
    });
  }, []);

  const dismissToast = useCallback(() => setToast(null), []);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="w-10 h-10 border-2 border-zinc-700 border-t-sky-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <AuthView />;
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="mx-auto max-w-md min-h-screen bg-zinc-950 relative shadow-2xl">
        <Header onOpenDrawer={() => setDrawerOpen(true)} onSearchClick={() => {}} />
        <main>
          {showBookmarks ? (
            <BookmarksView onBack={() => setShowBookmarks(false)} />
          ) : (
            <>
              {activeTab === 'feed' && <FeedView />}
              {activeTab === 'ai' && <AIView />}
              {activeTab === 'profile' && (
                <ProfileView user={user} onOpenBookmarks={() => setShowBookmarks(true)} />
              )}
            </>
          )}
        </main>
        <BottomNav active={activeTab} onChange={setActiveTab} />
      </div>
      <SideDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} onLockedCategory={showLockedToast} />
      <Toast toast={toast} onDismiss={dismissToast} />
    </div>
  );
}
export default App;