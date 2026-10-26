import { CheckCircle2, AlertTriangle, CircleDashed } from 'lucide-react';
import { getCorroboration, type Article } from '../lib/supabase';

type Props = { article: Pick<Article, 'agent_log'> };

/** Small badge: how many independent outlets report this story. Never claims more than the backend counted. */
export default function CorroborationBadge({ article }: Props) {
  const c = getCorroboration(article);
  if (!c) return null;
  if (c.status === 'corroborated') {
    return (
      <span className="inline-flex items-center gap-1 text-emerald-400" title={c.outlets.join(', ')}>
        <CheckCircle2 size={12} /><span className="font-semibold">Reported by {c.count} outlets</span>
      </span>
    );
  }
  if (c.status === 'single_source') {
    return (
      <span className="inline-flex items-center gap-1 text-amber-400" title="No other outlet found reporting this yet">
        <AlertTriangle size={12} /><span className="font-semibold">Single source</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-zinc-500" title="Not cross-checked against other outlets">
      <CircleDashed size={12} /><span>Not cross-checked</span>
    </span>
  );
}

/** Longer explanation for the article detail screen. */
export function CorroborationDetail({ article }: Props) {
  const c = getCorroboration(article);
  if (!c) return null;
  const text =
    c.status === 'corroborated'
      ? `Also confirmed by: ${c.outlets.join(', ')}. These are separate outlets reporting the same story.`
      : c.status === 'single_source'
        ? 'We could not find another outlet reporting this yet. Treat it with care until others confirm.'
        : 'This story was not cross-checked against other outlets.';
  return <p className="text-[11px] text-zinc-500 mb-3 leading-relaxed">{text}</p>;
}
