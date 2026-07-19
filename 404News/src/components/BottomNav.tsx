import { Newspaper, Sparkles, User } from 'lucide-react';
export type Tab = 'feed' | 'ai' | 'profile';
const tabs: { id: Tab; label: string; icon: typeof Newspaper }[] = [
  { id: 'feed', label: 'Feed', icon: Newspaper },
  { id: 'ai', label: 'AI', icon: Sparkles },
  { id: 'profile', label: 'Profile', icon: User },
];
export default function BottomNav({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md bg-zinc-950/95 backdrop-blur-sm border-t border-zinc-900 z-30">
      <div className="flex items-center justify-around h-16">
        {tabs.map((tab) => { const Icon = tab.icon; const isActive = active === tab.id; return (
          <button key={tab.id} onClick={() => onChange(tab.id)} className="flex flex-col items-center gap-0.5 py-1 px-6 transition-all">
            <Icon size={22} className={`transition-all ${isActive ? 'text-sky-400 scale-110' : 'text-zinc-600'}`} fill={isActive ? 'currentColor' : 'none'} />
            <span className={`text-[10px] font-semibold transition-colors ${isActive ? 'text-sky-400' : 'text-zinc-600'}`}>{tab.label}</span>
          </button> ); })}
      </div>
    </nav>
  );
}
