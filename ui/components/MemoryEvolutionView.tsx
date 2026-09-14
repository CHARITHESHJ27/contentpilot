"use client";

import { useEffect, useState } from "react";
import { Brain, AlertTriangle, ShieldCheck, ArrowRight, RefreshCw, GitCommit, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";

export default function MemoryEvolutionView() {
  const [evolutionData, setEvolutionData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.getEvolutionStatus()
      .then((data) => setEvolutionData(data))
      .catch((err) => console.error("Failed to load evolution status", err))
      .finally(() => setLoading(false));
  }, []);

  const apiTrends = evolutionData?.trends;
  const failurePatterns = (apiTrends && apiTrends.length > 0) ? apiTrends.map((t: any) => ({
    pattern_key: t.pattern_key,
    description: t.description,
    occurrences: t.occurrences,
    severity: t.occurrences >= 3 ? "CRITICAL" : "MAJOR",
    guardrail: t.recommended_guardrail,
    status: "ACTIVE GUARDRAIL",
  })) : [
    {
      pattern_key: "confusing_rag_with_model_training",
      description: "Claiming that adding documents to RAG retrains the model parameters.",
      occurrences: 4,
      severity: "CRITICAL",
      guardrail: "Explicitly state that retrieval operates strictly at inference time without modifying model weights.",
      status: "ACTIVE GUARDRAIL",
    },
    {
      pattern_key: "excessive_unexplained_jargon",
      description: "Using vector embeddings jargon without beginner-friendly definition.",
      occurrences: 2,
      severity: "MAJOR",
      guardrail: "Mandate glossary explanation whenever embeddings or vectors are first introduced.",
      status: "ACTIVE GUARDRAIL",
    },
  ];

  const evolutionSteps = [
    { name: "1. Failure Pattern", desc: "Gate detects recurring check failure" },
    { name: "2. Aggregation", desc: "FailurePattern table groups sample traces" },
    { name: "3. Proposal", desc: "System generates candidate prompt version" },
    { name: "4. Regression Eval", desc: "Golden eval suite verifies candidate" },
    { name: "5. Approval & Version", desc: "Candidate promoted to active v1.0.1" },
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-panel rounded-2xl p-6 border border-white/10 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
            <Brain className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Long-Term Memory & Controlled Self-Evolution</h2>
            <p className="text-xs text-slate-400">Detect recurring failure patterns across runs to inject dynamic prompt guardrails</p>
          </div>
        </div>

        <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
          Prompt Version: v1.0.0
        </span>
      </div>

      {/* Controlled Evolution Lifecycle Diagram */}
      <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-4">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <GitCommit className="w-4 h-4 text-purple-400" />
          Controlled Self-Evolution Loop (Observe ➔ Propose ➔ Evaluate ➔ Approve ➔ Version)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {evolutionSteps.map((step, idx) => (
            <div key={idx} className="p-3.5 rounded-xl bg-white/5 border border-white/10 space-y-1 text-center">
              <span className="text-xs font-bold text-purple-300 block">{step.name}</span>
              <p className="text-[11px] text-slate-400 leading-tight">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Active Failure Patterns Cards */}
      <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-4">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          Active Long-Term Failure Patterns & Guardrails
        </h3>

        <div className="space-y-3">
          {failurePatterns.map((pat: { pattern_key: string; description: string; occurrences: number; severity: string; guardrail: string; status: string }, idx: number) => (
            <div key={idx} className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-white text-xs">{pat.pattern_key}</span>
                  <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-400 font-bold text-[10px] border border-red-500/30">
                    {pat.severity}
                  </span>
                </div>

                <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> {pat.status}
                </span>
              </div>

              <p className="text-slate-300">{pat.description}</p>

              <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-200 font-medium space-y-1">
                <span className="font-bold text-[10px] uppercase text-purple-300 block">Injecting Guardrail into Generation Prompt:</span>
                <p>"{pat.guardrail}"</p>
              </div>

              <div className="text-[11px] text-slate-400 font-mono">
                Detected Occurrences Across Runs: <span className="text-white font-bold">{pat.occurrences}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
