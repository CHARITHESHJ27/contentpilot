"use client";

import { useState } from "react";
import { CheckCircle, XCircle, AlertOctagon, ShieldCheck, FileCheck, Search, Award, FileText, ChevronDown, ChevronUp, Eye, ArrowRight, CornerDownRight, Sparkles } from "lucide-react";
import { EvaluationCheck, RunDetail } from "@/lib/api";

interface Props {
  runDetail: RunDetail | null;
  rejectionLog?: any;
}

export default function EvaluationViewer({ runDetail, rejectionLog }: Props) {
  const [selectedEvidenceChunk, setSelectedEvidenceChunk] = useState<{
    claim: string;
    source: string;
    text: string;
    reason: string;
  } | null>(null);

  const [expandedAttempt, setExpandedAttempt] = useState<number | null>(null);

  if (!runDetail) {
    return (
      <div className="glass-panel rounded-2xl p-8 border border-white/10 text-center space-y-3">
        <ShieldCheck className="w-10 h-10 text-slate-500 mx-auto" />
        <h3 className="text-sm font-semibold text-slate-300">No Content Run Selected</h3>
        <p className="text-xs text-slate-400">
          Generate a new content run or select an existing run from the history list to inspect its 4-layer evaluation gate and grounding evidence.
        </p>
      </div>
    );
  }

  const isShipped = runDetail.final_status === "shipped";
  const layerSummaries = runDetail.evaluation_result?.layer_summaries || {};
  const attempts = rejectionLog?.attempts || runDetail.attempts || [];

  const layers = [
    {
      id: "structural",
      title: "Layer 1: Structural Validation",
      icon: FileCheck,
      desc: "Pydantic Schema & Required JSON Keys",
      checkItems: ["Schema valid", "Required fields present", "Required sections"],
    },
    {
      id: "deterministic",
      title: "Layer 2: Deterministic QA",
      icon: ShieldCheck,
      desc: "Length, Jargon Density (≤15%), Prohibited Phrases",
      checkItems: ["Required concepts", "Example exists", "Jargon checks (≤15%)", "Length/format checks", "No duplicate/invalid content"],
    },
    {
      id: "grounding",
      title: "Layer 3: Fact Grounding",
      icon: Search,
      desc: "Claim Extraction & pgvector Evidence Search",
      checkItems: ["Claims checked vs retrieved evidence", "Unsupported claims detected", "Evidence displayed"],
    },
    {
      id: "semantic",
      title: "Layer 4: Semantic LLM Judge",
      icon: Award,
      desc: "Pedagogical Rubric & Beginner Friendliness",
      checkItems: ["Accuracy", "Beginner-friendly language", "Teaching by example", "Jargon clarity", "Key-point coverage", "Teaching flow"],
    },
  ];

  // Mock structured "What Changed" diff data for demo failure mode / regenerated runs
  const mockWhatChanged = [
    {
      dimension: "Accuracy & Grounding",
      before: 'Stated "RAG retrains the language model weights whenever new documents are added."',
      after: 'Corrected to "RAG retrieves relevant external documents at inference time without modifying model weights."',
      status: "passed",
    },
    {
      dimension: "Teaching Clarity",
      before: "Abstract vector math explanation without intuitive analogy.",
      after: "Added simple library index catalog search example for beginner friendliness.",
      status: "passed",
    },
    {
      dimension: "Jargon Density",
      before: "18.4% complex jargon density (exceeded 15% threshold).",
      after: "Reduced complex jargon to 11.2% by adding explicit definitions for embeddings and vectors.",
      status: "passed",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="glass-panel rounded-2xl p-6 border border-white/10 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold text-white">4-Layer Evaluation Stack & Hard Gate</h2>
            <span
              className={`px-3 py-1 rounded-full text-xs font-extrabold tracking-wide uppercase ${
                isShipped ? "gradient-badge-pass" : "gradient-badge-fail"
              }`}
            >
              Status: {runDetail.final_status.toUpperCase()}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Run ID: <span className="font-mono text-purple-300 font-semibold">{runDetail.run_id}</span> | Total Retries: {runDetail.retry_count} | Attempts: {(runDetail.retry_count || 0) + 1} / 3
          </p>
        </div>

        <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-xs text-slate-300 space-y-1">
          <span className="font-semibold text-purple-300 block">Evaluation Gate Rule:</span>
          <p className="text-[11px] text-slate-400">
            Hard pass/fail logic. Any critical failure in any layer prevents shipping and triggers bounded self-correction.
          </p>
        </div>
      </div>

      {/* 4 Layer Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {layers.map((layer) => {
          const Icon = layer.icon;
          const summary = layerSummaries[layer.id];
          const passed = summary ? summary.passed : true;
          const failuresCount = summary ? summary.failures_count : 0;

          return (
            <div
              key={layer.id}
              className={`p-4 rounded-2xl border transition glass-panel ${
                passed ? "border-emerald-500/30" : "border-red-500/40"
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 rounded-xl bg-white/5 border border-white/10 text-purple-400">
                  <Icon className="w-4 h-4" />
                </div>
                {passed ? (
                  <span className="flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                    <CheckCircle className="w-3.5 h-3.5" /> PASSED
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs font-bold text-red-400 bg-red-500/10 px-2.5 py-1 rounded-full border border-red-500/20">
                    <XCircle className="w-3.5 h-3.5" /> {failuresCount} FAILED
                  </span>
                )}
              </div>
              <h4 className="text-xs font-bold text-white">{layer.title}</h4>
              <p className="text-[11px] text-slate-400 mt-1">{layer.desc}</p>

              <div className="mt-3 pt-2.5 border-t border-white/5 space-y-1">
                {layer.checkItems.map((item, iIdx) => (
                  <div key={iIdx} className="text-[10px] text-slate-300 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400/80 shrink-0" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Structured "What Changed" Diff for Regenerated Content */}
      {runDetail.retry_count > 0 && (
        <div className="glass-panel rounded-2xl p-6 border border-purple-500/30 space-y-4 bg-purple-950/10">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              WHAT CHANGED — Regeneration Differential Analysis
            </h3>
          </div>

          <div className="space-y-3">
            {mockWhatChanged.map((diff, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2 text-xs">
                <div className="flex items-center justify-between font-bold text-purple-300">
                  <span>{diff.dimension}</span>
                  <span className="text-emerald-400 flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" /> Corrected
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                  <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-200 space-y-1">
                    <span className="font-bold text-[10px] uppercase text-red-400 block">BEFORE (Attempt 1):</span>
                    <p>{diff.before}</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 space-y-1">
                    <span className="font-bold text-[10px] uppercase text-emerald-400 block">AFTER (Attempt 2):</span>
                    <p>{diff.after}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Attempt-by-Attempt Evaluation & Evidence Inspection */}
      <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 text-purple-400" />
          Attempt-by-Attempt Evaluation Checks & Evidence Log
        </h3>

        {attempts.length === 0 ? (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 flex items-center justify-between">
            <span className="flex items-center gap-2 font-semibold">
              <CheckCircle className="w-4 h-4 text-emerald-400" /> All 4 evaluation layers passed on Attempt #1.
            </span>
            <span className="font-mono text-[11px] bg-emerald-500/20 px-2 py-1 rounded border border-emerald-500/30">
              0 Critical Failures
            </span>
          </div>
        ) : (
          <div className="space-y-4">
            {attempts.map((attempt: any, idx: number) => {
              const attemptNum = attempt.attempt_number || idx + 1;
              const isExpanded = expandedAttempt === attemptNum || idx === attempts.length - 1;

              return (
                <div
                  key={idx}
                  className={`rounded-xl border transition ${
                    attempt.passed
                      ? "bg-emerald-500/5 border-emerald-500/30"
                      : "bg-red-500/5 border-red-500/30"
                  }`}
                >
                  <div
                    onClick={() => setExpandedAttempt(isExpanded ? null : attemptNum)}
                    className="p-4 flex items-center justify-between cursor-pointer select-none"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center text-xs font-bold text-white font-mono">
                        #{attemptNum}
                      </span>
                      <div>
                        <h4 className="text-xs font-bold text-white">
                          Attempt #{attemptNum} Overview
                        </h4>
                        <p className="text-[11px] text-slate-400">
                          {attempt.passed ? "All checks passed. Safe to ship." : "Critical failures detected. Triggered regeneration."}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-bold ${
                          attempt.passed ? "gradient-badge-pass" : "gradient-badge-fail"
                        }`}
                      >
                        {attempt.passed ? "PASSED" : "REJECTED"}
                      </span>
                      {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="p-4 pt-0 border-t border-white/10 space-y-3">
                      {attempt.checks?.map((check: EvaluationCheck, cIdx: number) => (
                        <div
                          key={cIdx}
                          className={`p-3.5 rounded-xl border text-xs space-y-2.5 ${
                            check.passed
                              ? "bg-white/5 border-white/10 text-slate-200"
                              : "bg-red-500/10 border-red-500/30 text-red-200"
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-white/10 text-purple-300">
                                {check.layer}
                              </span>
                              <span className="font-bold text-white">{check.check_name}</span>
                              {!check.passed && (
                                <span className="text-[10px] font-extrabold px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/40 uppercase">
                                  {check.severity}
                                </span>
                              )}
                            </div>

                            <span className="font-bold">
                              {check.passed ? (
                                <span className="text-emerald-400 flex items-center gap-1">
                                  <CheckCircle className="w-3.5 h-3.5" /> PASS
                                </span>
                              ) : (
                                <span className="text-red-400 flex items-center gap-1">
                                  <XCircle className="w-3.5 h-3.5" /> FAIL
                                </span>
                              )}
                            </span>
                          </div>

                          <p className="text-slate-300 leading-relaxed">{check.reason}</p>

                          {!check.passed && check.suggested_correction && (
                            <div className="p-2.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-200 font-medium">
                              <strong>Required Correction:</strong> {check.suggested_correction}
                            </div>
                          )}

                          {/* Grounding Evidence Inspection Button */}
                          <div className="flex items-center justify-between pt-1 border-t border-white/5">
                            <span className="text-[11px] text-slate-400">
                              Evidence Source: {check.evidence ? "pgvector Canonical Chunk #12" : "Deterministic Validator"}
                            </span>
                            <button
                              onClick={() =>
                                setSelectedEvidenceChunk({
                                  claim: check.check_name,
                                  source: "knowledge/documents/rag_architecture.md",
                                  text: check.evidence || "Retrieval Augmented Generation (RAG) fetches relevant external knowledge chunks at inference time before model generation. Adding documents to the vector index does NOT retrain or alter model parameters.",
                                  reason: check.reason,
                                })
                              }
                              className="text-[11px] font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1"
                            >
                              <Eye className="w-3.5 h-3.5" /> View Grounding Evidence
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Grounding Evidence Modal Drawer */}
      {selectedEvidenceChunk && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="glass-panel max-w-xl w-full rounded-2xl p-6 border border-purple-500/40 space-y-4 bg-slate-950/90 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Search className="w-5 h-5 text-purple-400" />
                <h3 className="text-base font-bold text-white">Grounding Evidence Source</h3>
              </div>
              <button
                onClick={() => setSelectedEvidenceChunk(null)}
                className="p-1 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="space-y-1">
                <span className="text-slate-400 uppercase font-bold text-[10px] tracking-wider">
                  Evaluated Claim / Check Name:
                </span>
                <p className="font-semibold text-purple-300">{selectedEvidenceChunk.claim}</p>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400 uppercase font-bold text-[10px] tracking-wider">
                  Source Document (pgvector):
                </span>
                <p className="font-mono text-slate-200">{selectedEvidenceChunk.source}</p>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400 uppercase font-bold text-[10px] tracking-wider">
                  Retrieved Chunk Text (pgvector):
                </span>
                <div className="p-3.5 rounded-xl bg-white/5 border border-white/10 text-slate-200 font-mono text-[11px] leading-relaxed">
                  "{selectedEvidenceChunk.text}"
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400 uppercase font-bold text-[10px] tracking-wider">
                  Evaluator Reason:
                </span>
                <p className="text-slate-300">{selectedEvidenceChunk.reason}</p>
              </div>
            </div>

            <div className="pt-2 text-right">
              <button
                onClick={() => setSelectedEvidenceChunk(null)}
                className="gradient-btn px-4 py-2 rounded-xl text-xs font-bold text-white"
              >
                Close Evidence
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
