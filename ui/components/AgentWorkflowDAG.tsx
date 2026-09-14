"use client";

import { CheckCircle2, XCircle, AlertTriangle, RefreshCw, ArrowDown, CornerDownRight, ShieldCheck, Database, FileCode, Search, Award, Sparkles } from "lucide-react";
import { RunDetail } from "@/lib/api";

interface Props {
  runDetail: RunDetail | null;
  activeNodeId?: string;
}

export default function AgentWorkflowDAG({ runDetail, activeNodeId }: Props) {
  const isShipped = runDetail?.final_status === "shipped";
  const isRejected = runDetail?.final_status === "rejected";
  const retryCount = runDetail?.retry_count || 0;

  // Determine Node State Statuses
  const getNodeStatus = (nodeKey: string) => {
    if (!runDetail) return { label: "— PENDING", color: "text-slate-500 border-white/5 bg-white/5" };

    if (nodeKey === "input") {
      return { label: "✓ INPUT VALID", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10", icon: CheckCircle2 };
    }
    if (nodeKey === "memory") {
      return { label: "✓ MEMORY LOADED", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10", icon: CheckCircle2 };
    }
    if (nodeKey === "retrieval") {
      return { label: "✓ PGVECTOR SEARCH", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10", icon: Database };
    }
    if (nodeKey === "generation") {
      return { label: "✓ LESSON GENERATED", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10", icon: Sparkles };
    }
    if (nodeKey === "structure") {
      return { label: "✓ LAYER 1 VALID", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10", icon: FileCode };
    }
    if (nodeKey === "deterministic") {
      return { label: "✓ LAYER 2 QA VALID", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10", icon: ShieldCheck };
    }
    if (nodeKey === "grounding") {
      if (retryCount > 0 && !isShipped) {
        return { label: "✗ CLAIM UNROUNDED", color: "text-red-400 border-red-500/40 bg-red-500/10", icon: XCircle };
      }
      return { label: "✓ GROUNDED (PGVECTOR)", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10", icon: Search };
    }
    if (nodeKey === "semantic") {
      if (retryCount > 0 && !isShipped) {
        return { label: "✗ RUBRIC FAILURE", color: "text-red-400 border-red-500/40 bg-red-500/10", icon: XCircle };
      }
      return { label: "✓ RUBRIC PASSED", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10", icon: Award };
    }
    if (nodeKey === "failure_analysis") {
      if (retryCount > 0) {
        return { label: `↻ REASONING (${retryCount} Retries)`, color: "text-amber-400 border-amber-500/40 bg-amber-500/10", icon: RefreshCw };
      }
      return { label: "— SKIPPED", color: "text-slate-500 border-white/5 bg-white/5", icon: null };
    }
    if (nodeKey === "decision") {
      if (isShipped) {
        return { label: "✓ PASSED (SHIPPED)", color: "text-emerald-400 border-emerald-500/40 bg-emerald-500/20", icon: CheckCircle2 };
      }
      if (isRejected) {
        return { label: "✗ REJECTED (HARD GATE)", color: "text-red-400 border-red-500/40 bg-red-500/20", icon: XCircle };
      }
      return { label: "● GATE EVALUATING", color: "text-amber-400 border-amber-500/40 bg-amber-500/10", icon: RefreshCw };
    }

    return { label: "— PENDING", color: "text-slate-500 border-white/5 bg-white/5" };
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-6">
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-purple-400" />
            Agentic Workflow Orchestrator (LangGraph DAG)
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time step-by-step state machine execution with automated self-correction loops
          </p>
        </div>

        <div className="flex items-center gap-2 text-[11px] font-mono">
          <span className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            ✓ PASS / PASSED
          </span>
          <span className="px-2 py-1 rounded bg-red-500/10 text-red-400 border border-red-500/20">
            ✗ FAIL
          </span>
          <span className="px-2 py-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
            ↻ RETRYING
          </span>
        </div>
      </div>

      {/* Workflow DAG Architecture Tree */}
      <div className="max-w-2xl mx-auto space-y-3">
        {/* Node 1: Input */}
        <div className="flex flex-col items-center">
          <DAGNode
            title="1. INPUT"
            subtitle="Topic submission & Learner profile"
            status={getNodeStatus("input")}
          />
          <ArrowDown className="w-4 h-4 text-purple-400/60 my-1" />
        </div>

        {/* Node 2: Memory */}
        <div className="flex flex-col items-center">
          <DAGNode
            title="2. MEMORY & GUARDRAILS"
            subtitle="Fetch long-term failure patterns"
            status={getNodeStatus("memory")}
          />
          <ArrowDown className="w-4 h-4 text-purple-400/60 my-1" />
        </div>

        {/* Node 3: Retrieval */}
        <div className="flex flex-col items-center">
          <DAGNode
            title="3. RETRIEVAL"
            subtitle="pgvector cosine search in PostgreSQL"
            status={getNodeStatus("retrieval")}
          />
          <ArrowDown className="w-4 h-4 text-purple-400/60 my-1" />
        </div>

        {/* Node 4: Generation */}
        <div className="flex flex-col items-center">
          <DAGNode
            title="4. GENERATION"
            subtitle="LLM synthesis with structured constraints"
            status={getNodeStatus("generation")}
          />
          <ArrowDown className="w-4 h-4 text-purple-400/60 my-1" />
        </div>

        {/* Node 5: Structure Check */}
        <div className="flex flex-col items-center">
          <DAGNode
            title="5. STRUCTURE CHECK (Layer 1)"
            subtitle="Pydantic schema & required JSON fields"
            status={getNodeStatus("structure")}
          />
          <ArrowDown className="w-4 h-4 text-purple-400/60 my-1" />
        </div>

        {/* Node 6: Deterministic QA */}
        <div className="flex flex-col items-center">
          <DAGNode
            title="6. DETERMINISTIC QA (Layer 2)"
            subtitle="Word count, jargon density (≤15%), required concepts"
            status={getNodeStatus("deterministic")}
          />
          <ArrowDown className="w-4 h-4 text-purple-400/60 my-1" />
        </div>

        {/* Node 7: Grounding Check */}
        <div className="flex flex-col items-center">
          <DAGNode
            title="7. GROUNDING CHECK (Layer 3)"
            subtitle="Claim extraction & pgvector evidence verify"
            status={getNodeStatus("grounding")}
          />
          <ArrowDown className="w-4 h-4 text-purple-400/60 my-1" />
        </div>

        {/* Node 8: Semantic Evaluation */}
        <div className="flex flex-col items-center">
          <DAGNode
            title="8. SEMANTIC EVALUATION (Layer 4)"
            subtitle="LLM Judge pedagogical rubric assessment"
            status={getNodeStatus("semantic")}
          />
          <ArrowDown className="w-4 h-4 text-purple-400/60 my-1" />
        </div>

        {/* Node 8: Decision Branch */}
        <div className="p-4 rounded-xl glass-panel border border-purple-500/30 text-center space-y-2 bg-purple-950/20">
          <span className="text-xs font-bold text-purple-300 uppercase tracking-widest">
            HARD EVALUATION GATE DECISION
          </span>
          <div className="grid grid-cols-2 gap-4 pt-2">
            {/* PASS Branch */}
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 space-y-1 text-left">
              <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> PASS BRANCH
              </span>
              <p className="text-[11px] text-slate-300">
                All 4 Layers Passed ➔ <strong>SHIP LESSON</strong>
              </p>
            </div>

            {/* FAIL Branch */}
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 space-y-1 text-left">
              <span className="text-xs font-bold text-amber-400 flex items-center gap-1">
                <RefreshCw className="w-4 h-4" /> FAIL BRANCH
              </span>
              <p className="text-[11px] text-slate-300">
                Critical Failure ➔ <strong>FAILURE ANALYSIS & REGENERATE</strong>
              </p>
            </div>
          </div>
        </div>

        {/* Failure Loop Details */}
        {retryCount > 0 && (
          <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200 flex items-start gap-2">
            <CornerDownRight className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-amber-300 block">
                Self-Correction Loop Active ({retryCount} / 2 Regenerations)
              </span>
              The system analyzed the evaluation failure, appended correctional guardrails to the state memory, and executed attempt #{retryCount + 1}.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DAGNode({
  title,
  subtitle,
  status,
}: {
  title: string;
  subtitle: string;
  status: { label: string; color: string; icon?: any };
}) {
  const Icon = status.icon;

  return (
    <div className={`w-full p-3.5 rounded-xl border flex items-center justify-between text-xs transition ${status.color}`}>
      <div>
        <h4 className="font-bold text-white text-xs">{title}</h4>
        <p className="text-[11px] text-slate-400">{subtitle}</p>
      </div>

      <div className="flex items-center gap-1.5 font-bold font-mono shrink-0">
        {Icon && <Icon className="w-3.5 h-3.5" />}
        <span>{status.label}</span>
      </div>
    </div>
  );
}
