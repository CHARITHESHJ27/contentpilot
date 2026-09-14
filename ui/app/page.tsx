"use client";

import { useEffect, useState, useCallback } from "react";
import { Sparkles, FileText, ShieldCheck, Database, History, RefreshCw, GitBranch, AlertOctagon, Brain, Activity } from "lucide-react";
import GeneratorStudio from "@/components/GeneratorStudio";
import EvaluationViewer from "@/components/EvaluationViewer";
import LessonViewer from "@/components/LessonViewer";
import KnowledgeBaseManager from "@/components/KnowledgeBaseManager";
import RunStatusHeader from "@/components/RunStatusHeader";
import AgentWorkflowDAG from "@/components/AgentWorkflowDAG";
import RejectionLog from "@/components/RejectionLog";
import MemoryEvolutionView from "@/components/MemoryEvolutionView";
import ObservabilityPanel from "@/components/ObservabilityPanel";
import { api, RunSummary, RunDetail, LessonData } from "@/lib/api";

type Tab = "studio" | "workflow" | "lesson" | "evaluation" | "rejection" | "memory" | "knowledge";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("studio");
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [runDetail, setRunDetail] = useState<RunDetail | null>(null);
  const [lessonData, setLessonData] = useState<LessonData | null>(null);
  const [lessonVersion, setLessonVersion] = useState<number>(1);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const fetchRunsHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const data = await api.listRuns(20);
      setRuns(data);
      if (data.length > 0 && !selectedRunId) {
        setSelectedRunId(data[0].run_id);
      }
    } catch {
      // Backend starting or idle
    } finally {
      setLoadingHistory(false);
    }
  }, [selectedRunId]);

  const fetchRunDetails = useCallback(async (runId: string) => {
    try {
      const detail = await api.getRunDetail(runId);
      setRunDetail(detail);

      if (detail.lesson_version) {
        setLessonVersion(detail.lesson_version);
        const lessonRes = await api.getLesson(runId, detail.lesson_version);
        setLessonData(lessonRes.lesson);
      }
    } catch {
      // Handle gracefully
    }
  }, []);

  useEffect(() => {
    fetchRunsHistory();
  }, [fetchRunsHistory]);

  useEffect(() => {
    if (selectedRunId) {
      fetchRunDetails(selectedRunId);
    }
  }, [selectedRunId, fetchRunDetails]);

  const handleRunCreated = (newRunId: string) => {
    setSelectedRunId(newRunId);
    fetchRunsHistory();
    fetchRunDetails(newRunId);
    setActiveTab("workflow");
  };

  const handleVersionChange = async (ver: number) => {
    if (!selectedRunId) return;
    setLessonVersion(ver);
    try {
      const lessonRes = await api.getLesson(selectedRunId, ver);
      setLessonData(lessonRes.lesson);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Persistent Run Status Header */}
      <RunStatusHeader runDetail={runDetail} />

      {/* Observability Telemetry Panel */}
      <ObservabilityPanel runDetail={runDetail} />

      {/* Top Controls & Navigation Bar */}
      <div className="glass-panel rounded-2xl p-4 border border-white/10 flex flex-wrap items-center justify-between gap-4">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10 overflow-x-auto">
          <button
            onClick={() => setActiveTab("studio")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition shrink-0 ${
              activeTab === "studio"
                ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Generator Studio
          </button>

          <button
            onClick={() => setActiveTab("workflow")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition shrink-0 ${
              activeTab === "workflow"
                ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <GitBranch className="w-3.5 h-3.5 text-purple-300" />
            Agent Workflow
          </button>

          <button
            onClick={() => setActiveTab("lesson")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition shrink-0 ${
              activeTab === "lesson"
                ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Shipped Lesson
          </button>

          <button
            onClick={() => setActiveTab("evaluation")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition shrink-0 ${
              activeTab === "evaluation"
                ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            4-Layer Evaluation
          </button>

          <button
            onClick={() => setActiveTab("rejection")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition shrink-0 ${
              activeTab === "rejection"
                ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <AlertOctagon className="w-3.5 h-3.5 text-amber-300" />
            Rejection Log & Diff
          </button>

          <button
            onClick={() => setActiveTab("memory")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition shrink-0 ${
              activeTab === "memory"
                ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Brain className="w-3.5 h-3.5 text-purple-400" />
            Memory & Self-Evolution
          </button>

          <button
            onClick={() => setActiveTab("knowledge")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition shrink-0 ${
              activeTab === "knowledge"
                ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            pgvector Knowledge Base
          </button>
        </div>

        {/* History Dropdown */}
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-purple-400" />
          <select
            value={selectedRunId || ""}
            onChange={(e) => setSelectedRunId(e.target.value)}
            className="px-3 py-2 rounded-xl glass-input text-xs text-white max-w-[240px] truncate"
          >
            <option value="" disabled>Select Generation Run</option>
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id} className="bg-slate-900 text-white">
                {r.topic} ({r.final_status})
              </option>
            ))}
          </select>

          <button
            onClick={fetchRunsHistory}
            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-400 hover:text-white transition"
            title="Refresh Runs List"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Main Tab Content Display */}
      <div>
        {activeTab === "studio" && (
          <GeneratorStudio onRunCreated={handleRunCreated} />
        )}

        {activeTab === "workflow" && (
          <AgentWorkflowDAG runDetail={runDetail} />
        )}

        {activeTab === "lesson" && (
          <LessonViewer
            lessonData={lessonData}
            version={lessonVersion}
            totalVersions={runDetail?.lesson_versions_count || 1}
            onVersionChange={handleVersionChange}
          />
        )}

        {activeTab === "evaluation" && (
          <EvaluationViewer runDetail={runDetail} />
        )}

        {activeTab === "rejection" && (
          <RejectionLog runDetail={runDetail} />
        )}

        {activeTab === "memory" && (
          <MemoryEvolutionView />
        )}

        {activeTab === "knowledge" && (
          <KnowledgeBaseManager />
        )}
      </div>
    </div>
  );
}
