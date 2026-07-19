import { useState, useEffect } from 'react';
import { CheckCircle2, X } from 'lucide-react';

export interface ToastState { id: number; title: string; message: string; }

export default function Toast({ toast, onDismiss }: { toast: ToastState | null; onDismiss: () => void }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!toast) { setVisible(false); return; }
    setVisible(true);
    const timer = setTimeout(() => { setVisible(false); setTimeout(onDismiss, 300); }, 5000);
    return () => clearTimeout(timer);
  }, [toast, onDismiss]);
  if (!toast) return null;

  return (
    <div className={`fixed bottom-6 right-6 z-[100] transition-all duration-300 ${visible ? 'translate-x-0 opacity-100' : 'translate-x-[120%] opacity-0'}`}>
      <div className="w-80 rounded-2xl bg-zinc-900 border border-zinc-800 shadow-2xl shadow-black/50 overflow-hidden">
        <div className="h-1 bg-gradient-to-r from-sky-400 via-blue-500 to-sky-400" />
        <div className="p-4">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <CheckCircle2 size={18} className="text-sky-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white font-bold text-sm">{toast.title}</p>
              <p className="text-zinc-400 text-xs leading-relaxed mt-1">{toast.message}</p>
            </div>
            <button onClick={() => { setVisible(false); setTimeout(onDismiss, 300); }} className="text-zinc-600 hover:text-white transition-colors flex-shrink-0">
              <X size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
