import { useState, useEffect, useCallback } from 'react';
import { Bookmark, Cpu, FileText, ShieldCheck, PenTool, Clock } from 'lucide-react';
import { fetchBookmarks, fetchAgentRuns, type Bookmark as BookmarkType, type AgentRun } from '../lib/supabase';
const agentIcons: Record<string, typeof Cpu> = { collector: FileText, verification: ShieldCheck, presenter: PenTool };

export default function ProfileView() {
  const [bookmarks, setBookmarks] = useState<BookmarkType[]>([]);
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => { try { const [bm, runs] = await Promise.all([fetchBookmarks(), fetchAgentRuns()]); setBookmarks(bm); setAgentRuns(runs); } catch {} setLoading(false); }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="pt-4 pb-24 px-4">
      <div className="flex flex-col items-center mb-6">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center mb-3"><span className="text-2xl font-bold text-white">U</span></div>
        <h2 className="text-white font-bold text-xl">AI News Reader</h2><p className="text-zinc-500 text-sm mt-0.5">Member since today</p>
      </div>
      <div className="grid grid-cols-3 gap-2 mb-6">
        <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-3 text-center"><p className="text-2xl font-bold text-white">{bookmarks.length}</p><p className="text-[10px] text-zinc-500 font-semibold uppercase mt-0.5">Saved</p></div>
        <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-3 text-center"><p className="text-2xl font-bold text-white">{agentRuns.length}</p><p className="text-[10px] text-zinc-500 font-semibold uppercase mt-0.5">Runs</p></div>
        <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-3 text-center"><p className="text-2xl font-bold text-white">20</p><p className="text-[10px] text-zinc-500 font-semibold uppercase mt-0.5">Stories</p></div>
      </div>
      <h3 className="text-white font-bold text-sm mb-3 flex items-center gap-2"><Bookmark size={15} className="text-sky-400" /> Saved Stories</h3>
      {bookmarks.length === 0 ? (
        <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-6 text-center mb-6"><Bookmark size={24} className="text-zinc-700 mx-auto mb-2" /><p className="text-zinc-500 text-sm">No saved stories yet</p><p className="text-zinc-600 text-xs mt-1">Tap the bookmark icon on any story</p></div>
      ) : (<div className="space-y-2 mb-6">{bookmarks.map((bm) => (<div key={bm.id} className="rounded-xl bg-zinc-900 border border-zinc-800 p-3"><p className="text-white text-sm font-medium line-clamp-2">{bm.title}</p></div>))}</div>)}
      <h3 className="text-white font-bold text-sm mb-3 flex items-center gap-2"><Cpu size={15} className="text-sky-400" /> Agent Pipeline Log</h3>
      {loading ? (<div className="space-y-2">{[1, 2, 3].map((i) => <div key={i} className="h-16 rounded-xl bg-zinc-900 animate-pulse" />)}</div>) : (
        <div className="space-y-2">{agentRuns.map((run) => { const Icon = agentIcons[run.agent_name] ?? Cpu; return (
          <div key={run.id} className="rounded-xl bg-zinc-900 border border-zinc-800 p-3 animate-fadeIn">
            <div className="flex items-center gap-2 mb-1.5"><div className="w-7 h-7 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center"><Icon size={14} className="text-sky-400" /></div><div className="flex-1"><p className="text-white text-sm font-semibold capitalize">{run.agent_name}</p><div className="flex items-center gap-1 text-[10px] text-zinc-600"><Clock size={9} />{new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div></div><span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold">{run.status}</span></div>
            <p className="text-zinc-500 text-xs leading-relaxed">{run.detail}</p>
          </div> ); })}</div>
      )}
    </div>
  );
}
