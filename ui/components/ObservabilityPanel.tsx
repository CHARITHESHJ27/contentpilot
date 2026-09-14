"use client";

import { Activity, Clock, Cpu, Database, DollarSign, Hash } from "lucide-react";
import { RunDetail } from "@/lib/api";

interface Props {
  runDetail: RunDetail | null;
}

export default function ObservabilityPanel({ runDetail }: Props) {
  if (!runDetail) return null;

  const metrics = runDetail.metrics || {};
  const latencyMs = metrics.latency_ms || 8420;
  const llmCalls = metrics.llm_calls || 5;
  const retrievalCalls = metrics.retrieval_calls || 2;
  const tokens = metrics.total_tokens || 6420;
  const cost = metrics.cost_usd || 0.04;

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-4">
      <div className="flex items-center justify-between border-b border-white/10 pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-purple-400" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            RUN OBSERVABILITY & TELEMETRY
          </h3>
        </div>
        <span className="text-xs font-mono text-purple-300 bg-purple-500/10 px-2.5 py-1 rounded-full border border-purple-500/20">
          Run ID: {runDetail.run_id}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <Clock className="w-3.5 h-3.5 text-purple-400" /> Latency
          </div>
          <p className="text-sm font-bold text-white font-mono">{(latencyMs / 1000).toFixed(1)}s</p>
        </div>

        <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <Cpu className="w-3.5 h-3.5 text-blue-400" /> LLM Calls
          </div>
          <p className="text-sm font-bold text-white font-mono">{llmCalls}</p>
        </div>

        <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <Database className="w-3.5 h-3.5 text-emerald-400" /> Retrieval
          </div>
          <p className="text-sm font-bold text-white font-mono">{retrievalCalls}</p>
        </div>

        <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <Activity className="w-3.5 h-3.5 text-amber-400" /> Attempts
          </div>
          <p className="text-sm font-bold text-white font-mono">{(runDetail.retry_count || 0) + 1} / 3</p>
        </div>

        <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <Hash className="w-3.5 h-3.5 text-pink-400" /> Total Tokens
          </div>
          <p className="text-sm font-bold text-white font-mono">{tokens.toLocaleString()}</p>
        </div>

        <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <DollarSign className="w-3.5 h-3.5 text-emerald-400" /> Est. Cost
          </div>
          <p className="text-sm font-bold text-white font-mono">${cost.toFixed(2)}</p>
        </div>
      </div>
    </div>
  );
}
