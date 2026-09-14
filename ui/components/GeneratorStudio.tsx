"use client";

import { useState } from "react";
import { Play, AlertTriangle, CheckCircle2, Loader2, Sparkles, BookOpen, User, Settings2 } from "lucide-react";
import { api, LearnerProfile } from "@/lib/api";

interface Props {
  onRunCreated: (runId: string) => void;
}

const WORKFLOW_STEPS = [
  { id: "load_memory", name: "Load Memory & Guardrails" },
  { id: "plan_curriculum", name: "Plan Curriculum Outline" },
  { id: "retrieve_knowledge", name: "RAG Vector Search (pgvector)" },
  { id: "generate_lesson", name: "LLM Lesson Synthesis" },
  { id: "evaluate", name: "4-Layer Gate Evaluation" },
  { id: "failure_analysis", name: "Self-Correction & Shipping" },
];

export default function GeneratorStudio({ onRunCreated }: Props) {
  const [topic, setTopic] = useState("Retrieval-Augmented Generation (RAG) Systems");
  const [profile, setProfile] = useState<LearnerProfile>({
    age_group: "17-18",
    education_level: "12th grade graduate",
    language_background: "non-English-medium",
    vocabulary_level: "limited English",
    career_goal: "start an AI career",
    country: "India",
  });

  const [demoMode, setDemoMode] = useState<string | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(-1);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleStartGeneration = async () => {
    if (!topic.trim()) return;
    setIsExecuting(true);
    setErrorMsg(null);
    setActiveStepIndex(0);

    try {
      // Step simulation indicator
      const interval = setInterval(() => {
        setActiveStepIndex((prev) => {
          if (prev < WORKFLOW_STEPS.length - 1) return prev + 1;
          clearInterval(interval);
          return prev;
        });
      }, 1200);

      const res = await api.createRun({
        topic: topic.trim(),
        learner_profile: profile,
        demo_mode: demoMode,
      });

      clearInterval(interval);
      setActiveStepIndex(WORKFLOW_STEPS.length - 1);
      onRunCreated(res.run_id);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to launch generation run.");
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Generator Studio</h2>
            <p className="text-xs text-slate-400">Configure topic & learner profile for agentic generation</p>
          </div>
        </div>

        {/* Demo Mode Toggle */}
        <div className="flex items-center gap-2 bg-white/5 p-1 rounded-xl border border-white/10 text-xs">
          <button
            onClick={() => setDemoMode(null)}
            className={`px-3 py-1.5 rounded-lg transition font-medium ${
              demoMode === null
                ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Standard Run
          </button>
          <button
            onClick={() => setDemoMode("deliberate_failure")}
            className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 font-medium ${
              demoMode === "deliberate_failure"
                ? "bg-amber-600 text-white shadow-md shadow-amber-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-300" />
            Demo Failure Mode
          </button>
        </div>
      </div>

      {/* Topic Input */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-slate-300 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-purple-400" />
            Target Content Topic & Context
          </label>
          <span className={`text-[11px] font-mono ${topic.length > 4000 ? "text-red-400 font-bold" : "text-slate-400"}`}>
            {topic.length} / 4000 chars
          </span>
        </div>
        <textarea
          rows={3}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. Retrieval-Augmented Generation (RAG) Systems, or paste prompt requirements"
          className="w-full px-4 py-3 rounded-xl glass-input text-sm text-white placeholder-slate-500 resize-y"
        />
      </div>

      {/* Learner Profile Configuration Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white/5 p-4 rounded-xl border border-white/10">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-purple-400" />
            Age Group
          </label>
          <select
            value={profile.age_group}
            onChange={(e) => setProfile({ ...profile, age_group: e.target.value })}
            className="w-full px-3 py-2 rounded-lg glass-input text-xs text-white"
          >
            <option value="17-18">17-18 years old</option>
            <option value="19-22">19-22 years old</option>
            <option value="Adult Learner">Adult Learner</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
            <Settings2 className="w-3.5 h-3.5 text-purple-400" />
            Vocabulary Level
          </label>
          <select
            value={profile.vocabulary_level}
            onChange={(e) => setProfile({ ...profile, vocabulary_level: e.target.value })}
            className="w-full px-3 py-2 rounded-lg glass-input text-xs text-white"
          >
            <option value="limited English">Limited English (Simplest)</option>
            <option value="intermediate">Intermediate English</option>
            <option value="advanced">Advanced Technical</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            Career Goal
          </label>
          <select
            value={profile.career_goal}
            onChange={(e) => setProfile({ ...profile, career_goal: e.target.value })}
            className="w-full px-3 py-2 rounded-lg glass-input text-xs text-white"
          >
            <option value="start an AI career">Start an AI Career</option>
            <option value="pass certification">Pass Tech Exam</option>
            <option value="software developer">Software Engineer</option>
          </select>
        </div>
      </div>

      {/* Action Button */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={handleStartGeneration}
          disabled={isExecuting || !topic.trim()}
          className="gradient-btn px-6 py-3 rounded-xl text-sm font-semibold text-white flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isExecuting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Running Agentic Workflow...
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-white" />
              Generate Content Run
            </>
          )}
        </button>

        {demoMode === "deliberate_failure" && (
          <p className="text-xs text-amber-400/90 flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            Will trigger Layer 2 jargon density failure to demo self-correction retry
          </p>
        )}
      </div>

      {errorMsg && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Live LangGraph Execution Visualizer */}
      {(isExecuting || activeStepIndex >= 0) && (
        <div className="space-y-3 pt-4 border-t border-white/10">
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            LangGraph Execution Progress
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
            {WORKFLOW_STEPS.map((step, idx) => {
              const isCurrent = isExecuting && idx === activeStepIndex;
              const isDone = idx < activeStepIndex || (!isExecuting && activeStepIndex >= 0);

              return (
                <div
                  key={step.id}
                  className={`p-3 rounded-xl border text-center transition ${
                    isCurrent
                      ? "bg-purple-500/20 border-purple-500 text-purple-300 pulse-glow"
                      : isDone
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                      : "bg-white/5 border-white/5 text-slate-500"
                  }`}
                >
                  <div className="flex items-center justify-center mb-1.5">
                    {isCurrent ? (
                      <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                    ) : isDone ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <div className="w-2 h-2 rounded-full bg-slate-600" />
                    )}
                  </div>
                  <span className="text-[11px] font-medium leading-tight block">
                    {step.name}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
