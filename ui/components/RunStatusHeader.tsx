"use client";

import { CheckCircle2, XCircle, AlertTriangle, Clock, RefreshCw, Cpu, BookOpen, Layers, ShieldCheck, Tag } from "lucide-react";
import { RunDetail } from "@/lib/api";

interface Props {
  runDetail: RunDetail | null;
  currentAttempt?: number;
  maxAttempts?: number;
}

export default function RunStatusHeader({
  runDetail,
  currentAttempt = 1,
  maxAttempts = 3,
}: Props) {
  if (!runDetail) {
    return (
      <div className="glass-panel rounded-2xl p-4 border border-white/10 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-purple-400" />
          <span>No active content run selected. Launch a run in Generator Studio or select from history.</span>
        </div>
        <span className="font-mono text-slate-500">Max Attempts: {maxAttempts}</span>
      </div>
    );
  }

  const isPassed = runDetail.final_status === "shipped";
  const isRejected = runDetail.final_status === "rejected";
  const isFailed = runDetail.final_status === "failed";
  const isPending = runDetail.final_status === "pending";

  const attemptsCount = (runDetail.retry_count || 0) + 1;
  const regenerationsCount = runDetail.retry_count || 0;

  return (
    <div className="glass-panel rounded-2xl p-5 border border-white/10 space-y-4">
      {/* Top Banner Row */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-bold text-white tracking-wide">
              {runDetail.topic}
            </h3>
            {/* Status Pill */}
            {isPassed && (
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5 shadow-sm shadow-emerald-500/20">
                <CheckCircle2 className="w-3.5 h-3.5" />
                SHIPPED
              </span>
            )}
            {isRejected && (
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30 flex items-center gap-1.5 shadow-sm shadow-red-500/20">
                <XCircle className="w-3.5 h-3.5" />
                {runDetail.retry_count >= 2 ? "REJECTED (Max Retries Reached)" : "REJECTED (Quality Gate Failed)"}
              </span>
            )}
            {isFailed && (
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center gap-1.5 shadow-sm shadow-rose-500/20">
                <AlertTriangle className="w-3.5 h-3.5" />
                SYSTEM ERROR
              </span>
            )}
            {isPending && (
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center gap-1.5 animate-pulse">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                EXECUTING AGENT WORKFLOW
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Run ID: <span className="text-purple-300 font-semibold">{runDetail.run_id}</span>
          </p>
        </div>

        {/* Attempt Counter Badge */}
        <div className="flex items-center gap-4 bg-white/5 px-4 py-2 rounded-xl border border-white/10">
          <div className="text-right">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block">
              Attempt Progress
            </span>
            <span className="text-sm font-extrabold text-white">
              {attemptsCount} / {maxAttempts}
            </span>
          </div>
          <div className="h-6 w-px bg-white/10" />
          <div className="text-right">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block">
              Regenerations
            </span>
            <span className="text-sm font-extrabold text-purple-300">
              {regenerationsCount}
            </span>
          </div>
        </div>
      </div>

      {/* Error Alert if execution failed */}
      {runDetail.error && (
        <div className="rounded-xl p-3 bg-red-500/10 border border-red-500/30 flex items-start gap-3 text-xs text-red-200">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div className="space-y-1 overflow-hidden">
            <div className="font-semibold text-red-300">System Execution Error</div>
            <div className="font-mono text-[11px] text-red-200/90 break-all">{runDetail.error}</div>
          </div>
        </div>
      )}

      {/* Workflow Check System Checklist */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Memory</span>
          <span className="text-emerald-400 font-bold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> ✓
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Retrieval</span>
          <span className="text-emerald-400 font-bold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> ✓
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Generation</span>
          <span className="text-emerald-400 font-bold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> ✓
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Validation</span>
          <span className="text-emerald-400 font-bold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> ✓
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Evaluation</span>
          <span className={isPassed ? "text-emerald-400 font-bold" : isRejected ? "text-red-400 font-bold" : "text-amber-400 font-bold"}>
            {isPassed ? "✓ Pass" : isRejected ? "✗ Fail" : "● Gate"}
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Decision</span>
          <span className={isPassed ? "text-emerald-400 font-bold" : isRejected ? "text-red-400 font-bold" : "text-amber-400 font-bold"}>
            {isPassed ? "Shipped" : isRejected ? "Rejected" : "Pending"}
          </span>
        </div>
      </div>

      {/* Metadata Configuration Footer */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-400 pt-2 border-t border-white/5">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-purple-400" />
            Model: <strong className="text-slate-200">{runDetail.model_version || "gpt-4o"}</strong>
          </span>
          <span className="flex items-center gap-1">
            <Tag className="w-3 h-3 text-blue-400" />
            Prompt: <strong className="text-slate-200">{runDetail.prompt_version || "1.0.0"}</strong>
          </span>
          <span className="flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            Rubric: <strong className="text-slate-200">{runDetail.rubric_version || "1.0.0"}</strong>
          </span>
          <span className="flex items-center gap-1">
            <BookOpen className="w-3 h-3 text-amber-400" />
            KB: <strong className="text-slate-200">v1.0.0 (pgvector)</strong>
          </span>
        </div>

        <div className="text-slate-500 font-mono">
          Bounded Limit: 3 Total Attempts (1 Initial + 2 Retries)
        </div>
      </div>
    </div>
  );
}
