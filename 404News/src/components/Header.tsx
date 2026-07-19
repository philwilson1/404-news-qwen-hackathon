import { Menu, Search, FileText } from 'lucide-react';
export default function Header({ onOpenDrawer, onSearchClick }: { onOpenDrawer: () => void; onSearchClick: () => void }) {
  return (
    <header className="sticky top-0 z-30 bg-zinc-950/95 backdrop-blur-sm border-b border-zinc-900">
      <div className="flex items-center justify-between px-4 h-14">
        <button onClick={onOpenDrawer} className="p-1.5 -ml-1.5 text-zinc-400 hover:text-white transition-colors"><Menu size={20} /></button>
        <div className="flex items-center gap-1.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center"><FileText size={16} className="text-white" /></div>
          <span className="text-white font-bold text-lg tracking-tight">404News<span className="text-sky-400">AI</span></span>
        </div>
        <button onClick={onSearchClick} className="p-1.5 -mr-1.5 text-zinc-400 hover:text-white transition-colors"><Search size={20} /></button>
      </div>
    </header>
  );
}
