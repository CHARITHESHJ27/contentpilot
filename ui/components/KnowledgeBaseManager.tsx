"use client";

import { useState } from "react";
import { Database, FileText, RefreshCw, CheckCircle, AlertTriangle, Layers } from "lucide-react";
import { api, IngestResponse } from "@/lib/api";

import PgvectorSandbox from "@/components/pgvectorSandbox";

export default function KnowledgeBaseManager() {
  const [ingesting, setIngesting] = useState(false);
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleTriggerIngestion = async () => {
    setIngesting(true);
    setError(null);
    try {
      const res = await api.ingestKnowledge();
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Ingestion failed");
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">pgvector Knowledge Base Index</h2>
              <p className="text-xs text-slate-400">Manage RAG vector embeddings stored in PostgreSQL</p>
            </div>
          </div>

          <button
            onClick={handleTriggerIngestion}
            disabled={ingesting}
            className="gradient-btn px-4 py-2.5 rounded-xl text-xs font-semibold text-white flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${ingesting ? "animate-spin" : ""}`} />
            {ingesting ? "Ingesting Documents..." : "Re-Ingest Knowledge Base"}
          </button>
        </div>

        {/* Info Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-1">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <FileText className="w-3.5 h-3.5 text-purple-400" />
              Documents Directory
            </div>
            <p className="text-sm font-bold text-white font-mono">knowledge/documents/</p>
          </div>

          <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-1">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Layers className="w-3.5 h-3.5 text-blue-400" />
              Vector Table
            </div>
            <p className="text-sm font-bold text-white font-mono">knowledge_chunks (pgvector)</p>
          </div>

          <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-1">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              Embedding Dimensions
            </div>
            <p className="text-sm font-bold text-white font-mono">1536 (text-embedding-3-small)</p>
          </div>
        </div>

        {result && (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 space-y-2">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold">
              <CheckCircle className="w-4 h-4" /> Ingestion Completed Successfully
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs text-slate-300">
              <div>Documents: <span className="font-bold text-white">{result.documents}</span></div>
              <div>Vector Chunks: <span className="font-bold text-white">{result.chunks}</span></div>
              <div>Version: <span className="font-bold text-white">{result.kb_version}</span></div>
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Interactive Similarity Search Sandbox */}
      <PgvectorSandbox />
    </div>
  );
}
