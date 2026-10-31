import { useEffect, useState } from 'react';
import { fetchPublishedBreaches, type Breach } from '../lib/supabase';
import BreachCard, { type CyberMode } from './BreachCard';

const MODE_KEY = 'cyber_mode';

function readMode(): CyberMode {
  try { return localStorage.getItem(MODE_KEY) === 'analyst' ? 'analyst' : 'simple'; } catch { return 'simple'; }
}

export default function CyberView() {
  const [mode, setMode] = useState<CyberMode>(readMode);
  const [breaches, setBreaches] = useState<Breach[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    fetchPublishedBreaches().then((b) => { if (alive) { setBreaches(b); setLoading(false); } });
    return () => { alive = false; };
  }, []);

  const choose = (m: CyberMode) => {
    setMode(m);
    try { localStorage.setItem(MODE_KEY, m); } catch { /* storage unavailable: mode just won't persist */ }
  };

  return (
    <div className="pb-20">
      <div className="flex items-center justify-between px-4 pt-3 pb-2">
        <h2 className="text-white font-bold text-base">Cybersecurity</h2>
        <div role="group" aria-label="Detail level" className="flex bg-zinc-900 border border-zinc-800 rounded-full p-0.5 text-[11px]">
          {(['simple', 'analyst'] as const).map((m) => (
            <button
              key={m}
              onClick={() => choose(m)}
              aria-pressed={mode === m}
              className={`px-3 py-1 rounded-full capitalize transition-colors ${mode === m ? 'bg-sky-500/15 text-sky-300' : 'text-zinc-500'}`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-zinc-700 border-t-sky-500 rounded-full animate-spin" />
        </div>
      ) : breaches.length === 0 ? (
        <p className="px-4 py-16 text-center text-sm text-zinc-500">No breaches published yet. Check back soon.</p>
      ) : (
        breaches.map((b) => <BreachCard key={b.id} breach={b} mode={mode} />)
      )}
    </div>
  );
}
