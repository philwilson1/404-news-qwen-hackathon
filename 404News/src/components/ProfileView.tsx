// src/components/ProfileView.tsx
import { signOut, type AuthUser } from '../lib/supabase';
import { LogOut, Bookmark, ChevronRight } from 'lucide-react';

interface ProfileViewProps {
  user: AuthUser;
  onOpenBookmarks: () => void;
}

export default function ProfileView({ user, onOpenBookmarks }: ProfileViewProps) {
  const meta = user?.user_metadata || (user as any)?.raw_user_meta_data || {};

  const displayName =
    meta.full_name ||
    meta.name ||
    meta.display_name ||
    meta.username ||
    (meta.first_name ? `${meta.first_name} ${meta.last_name || ''}`.trim() : null) ||
    user?.email?.split('@')[0] ||
    'User';

  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div className="pb-20 pt-4 px-4 max-w-3xl mx-auto">
      {/* Profile Header */}
      <div className="text-center my-6">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-tr from-sky-500 to-blue-600 text-white font-bold text-2xl mb-3 shadow-lg shadow-sky-500/20">
          {initial}
        </div>
        <h2 className="text-white font-bold text-xl">{displayName}</h2>
        <p className="text-zinc-500 text-xs mt-1">{user?.email}</p>

        <button
          onClick={() => signOut()}
          className="mt-4 inline-flex items-center gap-2 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-rose-400 text-xs px-4 py-2 rounded-xl transition-colors cursor-pointer"
        >
          <LogOut size={14} />
          Sign Out
        </button>
      </div>

      {/* Quick links */}
      <div className="mt-10 border-t border-zinc-800/80 pt-6 space-y-2">
        <button
          onClick={onOpenBookmarks}
          className="w-full flex items-center justify-between bg-zinc-900/90 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900 p-4 rounded-xl transition-all"
        >
          <div className="flex items-center gap-3">
            <Bookmark size={18} className="text-sky-400" />
            <span className="text-white font-semibold text-sm">Bookmarks</span>
          </div>
          <ChevronRight size={18} className="text-zinc-600" />
        </button>
      </div>
    </div>
  );
}