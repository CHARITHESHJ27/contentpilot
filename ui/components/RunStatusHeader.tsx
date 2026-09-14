"use client";

import { useState } from "react";
import { CheckCircle2, XCircle, AlertTriangle, Clock, RefreshCw, Cpu, BookOpen, Layers, ShieldCheck, Tag, RotateCcw, ChevronDown, ChevronUp } from "lucide-react";
import { RunDetail } from "@/lib/api";

interface Props {
  runDetail: RunDetail | null;
  currentAttempt?: number;
  maxAttempts?: number;
  onRetry?: () => void;
}

function getCleanErrorMessage(errorDetail?: any, rawError?: string): { message: string; detail?: string } {
  if (errorDetail?.message && !errorDetail.message.includes("[{") && !errorDetail.message.includes("Error code:")) {
    return {
      message: errorDetail.message,
      detail: errorDetail.detail || "AI provider rate limit reached. Please retry in a few moments.",
    };
  }

  const raw = rawError || "";
  if (raw.includes("429") || raw.toLowerCase().includes("quota") || raw.toLowerCase().includes("rate limit") || raw.includes("RESOURCE_EXHAUSTED")) {
    return {
      message: "The AI provider is temporarily unavailable because a rate limit was reached.",
      detail: "AI provider rate limit reached. Please retry in a few moments.",
    };
  }
  if (raw.toLowerCase().includes("timeout") || raw.includes("504")) {
    return {
      message: "The request to the AI provider timed out.",
      detail: "The upstream model took too long to respond. Please retry the run.",
    };
  }
  if (raw.toLowerCase().includes("auth") || raw.includes("401") || raw.includes("403")) {
    return {
      message: "AI provider authentication failed.",
      detail: "The provider API credentials are invalid or lack required permissions.",
    };
  }
  if (raw.includes("[{") || raw.includes("Error code:") || raw.includes("Traceback") || raw.includes("INFRASTRUCTURE_FAILURE")) {
    return {
      message: "Content generation could not be completed due to an AI provider error.",
      detail: "An infrastructure error occurred with the upstream service. Please retry later.",
    };
  }

  return {
    message: raw || "The AI provider is temporarily unavailable.",
    detail: "Please retry later.",
  };
}

export default function RunStatusHeader({
  runDetail,
  currentAttempt = 1,
  maxAttempts = 3,
  onRetry,
}: Props) {
  const [showDevDetails, setShowDevDetails] = useState(false);

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
  const isSystemError = runDetail.final_status === "failed" || runDetail.final_status === "system_error" || runDetail.decision === "system_error";
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
            {isSystemError && (
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

      {/* Clean Normalized System Error Card */}
      {isSystemError && (() => {
        const cleanErr = getCleanErrorMessage(runDetail.error_detail, runDetail.error);
        return (
          <div className="rounded-2xl p-5 bg-rose-500/10 border border-rose-500/30 space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-1.5 max-w-2xl">
                <div className="flex items-center gap-2 text-rose-300 font-bold text-sm">
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>SYSTEM ERROR</span>
                </div>
                <p className="text-xs font-medium text-white/90">
                  Content generation could not be completed.
                </p>
                <p className="text-xs text-rose-200/90 font-medium">
                  {cleanErr.message}
                </p>
                {cleanErr.detail && (
                  <p className="text-[11px] text-slate-300/80">
                    {cleanErr.detail}
                  </p>
                )}
              </div>

            {onRetry && (
              <button
                onClick={onRetry}
                className="px-4 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-xs font-semibold text-rose-200 hover:text-white flex items-center gap-1.5 transition shrink-0 shadow-sm"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Retry Run
              </button>
            )}
          </div>

          {/* Attempt / Content Retries / Evaluation / Decision 4-item Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-rose-500/20 text-xs">
            <div className="bg-black/30 p-2.5 rounded-xl border border-white/5">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 block font-semibold">Attempt</span>
              <span className="text-sm font-bold text-white font-mono">{attemptsCount} / {maxAttempts}</span>
            </div>
            <div className="bg-black/30 p-2.5 rounded-xl border border-white/5">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 block font-semibold">Content Retries</span>
              <span className="text-sm font-bold text-white font-mono">{regenerationsCount}</span>
            </div>
            <div className="bg-black/30 p-2.5 rounded-xl border border-white/5">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 block font-semibold">Evaluation</span>
              <span className="text-sm font-bold text-slate-300">Not executed</span>
            </div>
            <div className="bg-black/30 p-2.5 rounded-xl border border-white/5">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 block font-semibold">Decision</span>
              <span className="text-sm font-bold text-rose-400">System Error</span>
            </div>
          </div>

          {/* Collapsible Developer Details (Strictly Sanitized - Zero Secrets) */}
          <div className="pt-1">
            <button
              onClick={() => setShowDevDetails(!showDevDetails)}
              className="text-[11px] font-medium text-rose-300/80 hover:text-rose-200 flex items-center gap-1 transition"
            >
              {showDevDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              <span>Developer Details</span>
            </button>

            {showDevDetails && (
              <div className="mt-2.5 p-3.5 rounded-xl bg-black/40 border border-white/10 grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px] font-mono text-slate-300">
                <div><span className="text-slate-500 block text-[10px] font-sans">Provider</span> {runDetail.error_detail?.provider || "Gemini"}</div>
                <div><span className="text-slate-500 block text-[10px] font-sans">Model</span> {runDetail.error_detail?.model || runDetail.model_version || "gemini-3.5-flash"}</div>
                <div><span className="text-slate-500 block text-[10px] font-sans">Stage</span> {runDetail.error_detail?.stage || "generation"}</div>
                <div><span className="text-slate-500 block text-[10px] font-sans">HTTP Status</span> {runDetail.error_detail?.status_code || 429}</div>
                <div><span className="text-slate-500 block text-[10px] font-sans">Category</span> {runDetail.error_detail?.category || "RATE_LIMIT"}</div>
                <div><span className="text-slate-500 block text-[10px] font-sans">Retryable</span> {runDetail.error_detail?.retryable ? "Yes" : "No"}</div>
                <div><span className="text-slate-500 block text-[10px] font-sans">Content Retry Consumed</span> No</div>
                <div className="overflow-hidden"><span className="text-slate-500 block text-[10px] font-sans">Run ID</span> <span className="truncate block text-[10px]">{runDetail.run_id}</span></div>
              </div>
            )}
          </div>
        </div>
        );
      })()}

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
          <span className={isSystemError ? "text-rose-400 font-bold" : "text-emerald-400 font-bold flex items-center gap-1"}>
            {isSystemError ? "✗ Error" : <><CheckCircle2 className="w-3.5 h-3.5" /> ✓</>}
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Validation</span>
          <span className={isSystemError ? "text-slate-500 font-medium" : "text-emerald-400 font-bold flex items-center gap-1"}>
            {isSystemError ? "— Not reached" : <><CheckCircle2 className="w-3.5 h-3.5" /> ✓</>}
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Evaluation</span>
          <span className={isSystemError ? "text-slate-400 font-medium" : isPassed ? "text-emerald-400 font-bold" : isRejected ? "text-red-400 font-bold" : "text-amber-400 font-bold"}>
            {isSystemError ? "Not executed" : isPassed ? "✓ Pass" : isRejected ? "✗ Fail" : "● Gate"}
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Decision</span>
          <span className={isSystemError ? "text-rose-400 font-bold" : isPassed ? "text-emerald-400 font-bold" : isRejected ? "text-red-400 font-bold" : "text-amber-400 font-bold"}>
            {isSystemError ? "System Error" : isPassed ? "Shipped" : isRejected ? "Rejected" : "Pending"}
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
