import { useState, useCallback } from 'react';
import Header from './components/Header';
import BottomNav, { type Tab } from './components/BottomNav';
import SideDrawer from './components/SideDrawer';
import FeedView from './components/FeedView';
import AIView from './components/AIView';
import ProfileView from './components/ProfileView';
import Toast, { type ToastState } from './components/Toast';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('feed');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);

  const showLockedToast = useCallback(() => {
    setToast({
      id: Date.now(),
      title: 'Under Construction by the Agents',
      message: 'Our AI team is currently optimizing the data pipelines for this category. Stay tuned — greatness takes a little time.',
    });
  }, []);

  const dismissToast = useCallback(() => setToast(null), []);

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="mx-auto max-w-md min-h-screen bg-zinc-950 relative shadow-2xl">
        <Header onOpenDrawer={() => setDrawerOpen(true)} onSearchClick={() => {}} />
        <main>
          {activeTab === 'feed' && <FeedView />}
          {activeTab === 'ai' && <AIView />}
          {activeTab === 'profile' && <ProfileView />}
        </main>
        <BottomNav active={activeTab} onChange={setActiveTab} />
      </div>
      <SideDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} onLockedCategory={showLockedToast} />
      <Toast toast={toast} onDismiss={dismissToast} />
    </div>
  );
}
export default App;
