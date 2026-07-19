import { useState, useEffect, useRef, useCallback } from 'react';
import type { LucideIcon } from 'lucide-react';
import { FileSearch, ShieldCheck, PenTool, Check, ChevronDown, ArrowRight, Cpu } from 'lucide-react';

export type PipelineStatus = 'idle' | 'running' | 'done';

export interface PipelineStep {
  id: string;
  agentName: string;
  model: string;
  icon: LucideIcon;
  color: string;
  bgColor: string;
  borderColor: string;
  glowColor: string;
  logs: string[];
}

const STEPS: PipelineStep[] = [
  {
    id: 'collector',
    agentName: 'Collector Agent',
    model: 'qwen-coder',
    icon: FileSearch,
    color: 'text-sky-400',
    bgColor: 'bg-sky-500/10',
    borderColor: 'border-sky-500/30',
    glowColor: 'shadow-sky-500/20',
    logs: [
      'Initializing qwen-coder for source ingestion...',
      'Running chunk-and-discard on source data...',
      'Raw noise stripped. Context window optimized.',
      'JSON streams parsed from arXiv, GitHub, company blogs.',
    ],
  },
  {
    id: 'verification',
    agentName: 'Verification Agent',
    model: 'qwen3-max-thinking',
    icon: ShieldCheck,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/30',
    glowColor: 'shadow-emerald-500/20',
    logs: [
      'Loading qwen3-max-thinking with enable_thinking=true...',
      'preserve_thinking=true — reasoning chain retained.',
      'Cross-referencing GitHub commits and company blog...',
      '2+ independent sources matched. Factual credibility verified at 98%.',
    ],
  },
  {
    id: 'presenter',
    agentName: 'Presenter Agent',
    model: 'qwen3.7-max',
    icon: PenTool,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
    glowColor: 'shadow-amber-500/20',
    logs: [
      'Routing to qwen3.7-max for response synthesis...',
      'Rendering clean Markdown & embedding verified resources.',
      'Response compiled. Streaming to user...',
    ],
  },
];

interface AgentPipelineProps {
  active: boolean;
  onComplete: () => void;
}

export default function AgentPipeline({ active, onComplete }: AgentPipelineProps) {
  const [stepIndex, setStepIndex] = useState(-1);
  const [stepStatuses, setStepStatuses] = useState<PipelineStatus[]>(['idle', 'idle', 'idle']);
  const [visibleLogs, setVisibleLogs] = useState<string[]>([]);
  const [expanded, setExpanded] = useState(true);
  const [allDone, setAllDone] = useState(false);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = useCallback(() => { timersRef.current.forEach(clearTimeout); timersRef.current = []; }, []);

  const runPipeline = useCallback(() => {
    clearTimers();
    setStepIndex(-1);
    setStepStatuses(['idle', 'idle', 'idle']);
    setVisibleLogs([]);
    setAllDone(false);
    setExpanded(true);

    const stepDelay = 700;
    const logDelay = 500;

    STEPS.forEach((step, sIdx) => {
      const stepStart = sIdx * (stepDelay + step.logs.length * logDelay + 400);

      const t1 = setTimeout(() => {
        setStepIndex(sIdx);
        setStepStatuses((prev) => { const next = [...prev]; next[sIdx] = 'running'; return next; });
      }, stepStart);
      timersRef.current.push(t1);

      step.logs.forEach((log, lIdx) => {
        const t2 = setTimeout(() => {
          setVisibleLogs((prev) => [...prev, `[${step.agentName}] ${log}`]);
        }, stepStart + stepDelay + lIdx * logDelay);
        timersRef.current.push(t2);
      });

      const t3 = setTimeout(() => {
        setStepStatuses((prev) => { const next = [...prev]; next[sIdx] = 'done'; return next; });
        if (sIdx === STEPS.length - 1) {
          setAllDone(true);
          setStepIndex(-1);
          const t4 = setTimeout(() => { onComplete(); }, 600);
          timersRef.current.push(t4);
        }
      }, stepStart + stepDelay + step.logs.length * logDelay + 200);
      timersRef.current.push(t3);
    });
  }, [clearTimers, onComplete]);

  useEffect(() => { if (active) runPipeline(); else { clearTimers(); setStepIndex(-1); setStepStatuses(['idle', 'idle', 'idle']); setVisibleLogs([]); setAllDone(false); } }, [active, runPipeline, clearTimers]);
  useEffect(() => () => clearTimers(), [clearTimers]);

  const anyActive = stepStatuses.some((s) => s !== 'idle') || allDone;
  if (!anyActive) return null;

  return (
    <div className="rounded-2xl bg-zinc-900/80 border border-zinc-800 overflow-hidden animate-fadeIn mb-3">
      {/* Header */}
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Cpu size={14} className="text-white" />
            </div>
            {!allDone && <span className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" /><span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-sky-500" /></span>}
          </div>
          <div className="text-left">
            <p className="text-white text-sm font-bold">Multi-Agent Pipeline</p>
            <p className="text-[10px] text-zinc-500">{allDone ? 'Pipeline complete' : 'Agents processing your request...'}</p>
          </div>
        </div>
        <ChevronDown size={16} className={`text-zinc-500 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {/* Pipeline flow */}
      {expanded && (
        <div className="px-4 pb-3">
          {/* Agent steps visual flow */}
          <div className="flex items-center gap-1 mb-3">
            {STEPS.map((step, idx) => {
              const Icon = step.icon;
              const status = stepStatuses[idx];
              return (
                <div key={step.id} className="flex items-center flex-1">
                  <div className="relative flex flex-col items-center gap-1 flex-1">
                    <div className={`w-10 h-10 rounded-xl border flex items-center justify-center transition-all duration-300 ${status === 'done' ? `${step.bgColor} ${step.borderColor} shadow-lg ${step.glowColor}` : status === 'running' ? `${step.bgColor} ${step.borderColor} shadow-lg ${step.glowColor} scale-110` : 'bg-zinc-900 border-zinc-800'}`}>
                      <Icon size={18} className={status === 'done' || status === 'running' ? step.color : 'text-zinc-700'} />
                      {status === 'running' && <span className="absolute -top-1 -right-1 flex h-3 w-3"><span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ backgroundColor: step.color.includes('sky') ? '#38bdf8' : step.color.includes('emerald') ? '#34d399' : '#fbbf24' }} /><span className="relative inline-flex rounded-full h-3 w-3" style={{ backgroundColor: step.color.includes('sky') ? '#38bdf8' : step.color.includes('emerald') ? '#34d399' : '#fbbf24' }} /></span>}
                      {status === 'done' && <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-zinc-950 flex items-center justify-center"><Check size={9} className={step.color} strokeWidth={3} /></span>}
                    </div>
                    <span className={`text-[9px] font-bold ${status !== 'idle' ? step.color : 'text-zinc-700'}`}>{step.agentName.split(' ')[0]}</span>
                  </div>
                  {idx < STEPS.length - 1 && <ArrowRight size={14} className="text-zinc-700 flex-shrink-0 mx-0.5" />}
                </div>
              );
            })}
          </div>

          {/* Model badges */}
          <div className="flex items-center gap-1.5 mb-3">
            {STEPS.map((step, idx) => {
              const status = stepStatuses[idx];
              return (
                <div key={step.id} className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-md border ${status !== 'idle' ? `${step.bgColor} ${step.borderColor} border` : 'bg-zinc-900 border-zinc-800'}`}>
                  <span className={`text-[8px] font-mono font-bold ${status !== 'idle' ? step.color : 'text-zinc-700'}`}>{step.model}</span>
                </div>
              );
            })}
          </div>

          {/* API params row */}
          <div className="flex flex-wrap gap-1.5 mb-3">
            <span className="px-2 py-0.5 rounded-md bg-zinc-800/80 border border-zinc-700/50 text-[9px] font-mono text-zinc-500">enable_thinking: true</span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-800/80 border border-zinc-700/50 text-[9px] font-mono text-zinc-500">preserve_thinking: true</span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-800/80 border border-zinc-700/50 text-[9px] font-mono text-zinc-500">stream: true</span>
          </div>

          {/* Live log terminal */}
          <div className="rounded-xl bg-black/60 border border-zinc-800/50 p-3 max-h-32 overflow-y-auto no-scrollbar">
            <div className="space-y-1">
              {visibleLogs.map((log, i) => {
                const isLast = i === visibleLogs.length - 1;
                const step = STEPS.find((s) => log.startsWith(`[${s.agentName}]`));
                const agentColor = step?.color ?? 'text-zinc-400';
                const agentIcon = step?.icon;
                return (
                  <div key={i} className="flex items-start gap-2 animate-fadeIn">
                    {agentIcon ? <agentIcon size={11} className={`${agentColor} mt-0.5 flex-shrink-0`} /> : <span className="w-3 flex-shrink-0" />}
                    <p className={`text-[11px] font-mono leading-relaxed ${isLast ? 'text-zinc-300' : 'text-zinc-500'}`}>
                      <span className={agentColor}>{log.replace(/^\[.*?\]\s*/, '')}</span>
                      {isLast && !allDone && <span className="inline-block w-1.5 h-3 bg-sky-400 ml-0.5 animate-pulse align-middle" />}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
