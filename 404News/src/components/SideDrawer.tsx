import { X, Zap, ShieldCheck, FileText, PenTool, Github, Cpu, Lock, Trophy, Shirt, LineChart, GraduationCap } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface CategoryItem { id: string; label: string; icon: LucideIcon; locked: boolean; }
const categories: CategoryItem[] = [
  { id: 'ai-tech', label: 'AI & Technology', icon: Cpu, locked: false },
  { id: 'sports', label: 'Sports', icon: Trophy, locked: true },
  { id: 'fashion', label: 'Fashion', icon: Shirt, locked: true },
  { id: 'finance', label: 'Finance', icon: LineChart, locked: true },
  { id: 'education', label: 'Education', icon: GraduationCap, locked: true },
];

export default function SideDrawer({ open, onClose, onLockedCategory }: { open: boolean; onClose: () => void; onLockedCategory: () => void }) {
  return (
    <>
      <div className={`fixed inset-0 bg-black/60 z-40 transition-opacity ${open ? 'opacity-100' : 'opacity-0 pointer-events-none'}`} onClick={onClose} />
      <div className={`fixed top-0 left-0 h-full w-72 bg-zinc-950 border-r border-zinc-900 z-50 transition-transform duration-300 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between p-4 border-b border-zinc-900">
          <div className="flex items-center gap-2"><div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center"><Zap size={16} className="text-white" fill="white" /></div><span className="text-white font-bold text-lg">Pivot<span className="text-sky-400">AI</span></span></div>
          <button onClick={onClose} className="p-1 text-zinc-500 hover:text-white transition-colors"><X size={20} /></button>
        </div>
        <div className="p-4 overflow-y-auto no-scrollbar h-[calc(100%-73px)]">
          <p className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-3">PivotAI System</p>
          <div className="flex items-center gap-2 p-2.5 rounded-xl bg-zinc-900 border border-zinc-800 mb-4">
            <span className="flex h-2 w-2 relative"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" /><span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" /></span>
            <span className="text-white text-sm font-semibold">All Systems Operational</span>
          </div>

          <p className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-3">Multi-Agent System</p>
          <div className="space-y-2">
            {[{ icon: FileText, name: 'Collector', desc: 'Scrapes whitelisted AI sources' }, { icon: ShieldCheck, name: 'Verification', desc: 'Cross-checks 2+ independent sources' }, { icon: PenTool, name: 'Presenter', desc: 'Writes editorial hooks per vibe' }].map((agent) => { const Icon = agent.icon; return (
              <div key={agent.name} className="flex items-center gap-3 p-2.5 rounded-xl bg-zinc-900/50 border border-zinc-800"><div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center flex-shrink-0"><Icon size={16} className="text-sky-400" /></div><div><p className="text-white text-sm font-semibold">{agent.name}</p><p className="text-zinc-600 text-xs">{agent.desc}</p></div></div> ); })}
          </div>

          <div className="mt-6 pt-4 border-t border-zinc-900">
            <p className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-3">Categories</p>
            <div className="space-y-1">
              {categories.map((cat) => { const Icon = cat.icon; return (
                  <button key={cat.id} onClick={() => cat.locked && onLockedCategory()} className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all ${cat.locked ? 'bg-zinc-900/30 text-zinc-600 hover:bg-zinc-900/60' : 'bg-sky-500/10 border border-sky-500/20 text-sky-400'}`}>
                    <Icon size={16} className={cat.locked ? 'text-zinc-700' : 'text-sky-400'} />
                    <span className={`text-sm font-semibold flex-1 ${cat.locked ? 'text-zinc-600' : 'text-sky-400'}`}>{cat.label}</span>
                    {cat.locked && <Lock size={13} className="text-zinc-700" />}
                  </button> ); })}
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-zinc-900"><p className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest mb-3">About</p><p className="text-zinc-500 text-xs leading-relaxed">404News uses a 3-agent pipeline to collect, verify, and present AI news. Every story is checked against 2+ independent sources before publishing.</p></div>
          <div className="mt-6"><a href="#" className="flex items-center gap-2 text-zinc-500 hover:text-white text-sm transition-colors"><Github size={16} />View source</a></div>
        </div>
      </div>
    </>
  );
}
