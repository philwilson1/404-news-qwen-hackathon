import { useState } from 'react';
import { ExternalLink } from 'lucide-react';
import type { Breach } from '../lib/supabase';

export type CyberMode = 'simple' | 'analyst';

const safeUrl = (u: string) => (/^https?:\/\//i.test(u) ? u : null);
const fmtDate = (d: string) =>
  new Date(`${d}T00:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

export default function BreachCard({ breach, mode }: { breach: Breach; mode: CyberMode }) {
  const [expanded, setExpanded] = useState(false);
  const analyst = mode === 'analyst';
  const sources = (breach.sources || []).filter((s) => safeUrl(s.url));

  return (
    <article
      className="px-4 py-3 border-b border-zinc-900 animate-fadeIn cursor-pointer"
      onClick={() => setExpanded((v) => !v)}
    >
      <div className="flex items-center gap-2 mb-2 text-[11px] text-zinc-500">
        <span className="text-zinc-400 font-medium truncate">{breach.source_label}</span>
      </div>
      <h3 className="text-white font-bold leading-tight mb-1.5 text-base">{breach.headline}</h3>

      {!analyst && (
        <>
          <p className={`text-zinc-400 text-sm leading-relaxed ${expanded ? '' : 'line-clamp-3'}`}>{breach.what_happened}</p>
          {expanded && (
            <div className="mt-2 space-y-1.5 text-sm">
              {breach.affected && <p className="text-zinc-400"><span className="text-zinc-300 font-medium">Am I affected? </span>{breach.affected}</p>}
              {breach.what_to_do && <p className="text-zinc-400"><span className="text-zinc-300 font-medium">What you can do: </span>{breach.what_to_do}</p>}
            </div>
          )}
        </>
      )}

      {analyst && (
        <div className="text-xs">
          {breach.attacker && (
            <p className="text-zinc-400 mb-2">
              <span className="text-zinc-300 font-medium">Attacker: </span>{breach.attacker}
              {breach.attacker_assessed_by && <span className="text-zinc-500"> (assessed by {breach.attacker_assessed_by})</span>}
            </p>
          )}
          {breach.attack_chain?.map((s, i) => (
            <div key={i} className="flex gap-3 py-1.5 border-t border-zinc-900">
              <span className="w-24 flex-shrink-0 text-zinc-300 font-medium">{s.stage}</span>
              <div className="min-w-0 text-zinc-500">
                {s.attack_ids && s.attack_ids.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-0.5">
                    {s.attack_ids.map((id) => <span key={id} className="font-mono text-[10px] text-sky-400">{id}</span>)}
                  </div>
                )}
                {s.detail && <p>{s.detail}</p>}
                {s.soc_view && <p><span className="text-zinc-400">SOC: </span>{s.soc_view}</p>}
                {!s.detail && !s.soc_view && !(s.attack_ids && s.attack_ids.length) && <p className="text-zinc-600">Pending review</p>}
              </div>
            </div>
          ))}
          {breach.lessons?.length > 0 && (
            <div className="py-1.5 border-t border-zinc-900">
              <p className="text-zinc-300 font-medium mb-0.5">Lessons</p>
              <ul className="list-disc pl-4 text-zinc-500 space-y-0.5">
                {breach.lessons.map((l, i) => <li key={i}>{l}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mt-3 text-[11px] text-zinc-500">
        <div className="flex items-center gap-3">
          <span className={breach.root_cause === 'confirmed' ? 'text-emerald-400' : 'text-amber-400'}>
            Cause {breach.root_cause}
          </span>
          <span>Updated {fmtDate(breach.last_checked_on)}</span>
        </div>
        <div className="flex items-center gap-2">
          {sources.map((s, i) => (
            <a
              key={i}
              href={safeUrl(s.url)!}
              target="_blank"
              rel="noopener noreferrer"
              title={s.title}
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1 text-zinc-500 hover:text-sky-400 transition-colors"
            >
              <ExternalLink size={12} /> {i + 1}
            </a>
          ))}
        </div>
      </div>
    </article>
  );
}
