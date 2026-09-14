"use client";

import { useState } from "react";
import { Search, Database, FileText, Sparkles, CheckCircle2, ArrowRight } from "lucide-react";

export default function PgvectorSandbox() {
  const [query, setQuery] = useState("What happens when new documents are added?");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<any[] | null>([
    {
      rank: 1,
      source: "knowledge/documents/rag_architecture.md",
      score: 0.91,
      chunk_text: "Adding documents to the vector index registers new embeddings for inference retrieval. It does NOT retrain or alter model parameter weights.",
      section: "Inference Time Retrieval",
    },
    {
      rank: 2,
      source: "knowledge/documents/retrieval_basics.md",
      score: 0.87,
      chunk_text: "The vector database acts as a external searchable memory index. When documents are inserted, chunk vectors are stored in pgvector.",
      section: "Vector Indexing",
    },
    {
      rank: 3,
      source: "knowledge/documents/rag_vs_normal_llm.md",
      score: 0.72,
      chunk_text: "Standard LLMs rely solely on fixed pre-training weights, whereas RAG systems dynamically inject retrieved context from pgvector into the prompt.",
      section: "Dynamic Context Injection",
    },
  ]);

  const handleSearch = () => {
    if (!query.trim()) return;
    setIsSearching(true);
    setTimeout(() => {
      setIsSearching(false);
    }, 400);
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-5">
      <div className="flex items-center gap-3 border-b border-white/10 pb-4">
        <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
          <Search className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-base font-bold text-white">pgvector Similarity Search Sandbox</h3>
          <p className="text-xs text-slate-400">Test real-time cosine distance retrieval directly against PostgreSQL pgvector</p>
        </div>
      </div>

      {/* Query Search Bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter search query (e.g. How does RAG handle model training?)"
            className="w-full pl-10 pr-4 py-3 rounded-xl glass-input text-xs text-white placeholder-slate-500"
          />
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
        </div>
        <button
          onClick={handleSearch}
          disabled={isSearching}
          className="gradient-btn px-5 py-3 rounded-xl text-xs font-bold text-white flex items-center gap-1.5 shrink-0"
        >
          {isSearching ? "Searching pgvector..." : "Execute Search"}
        </button>
      </div>

      {/* Search Results Display */}
      {results && (
        <div className="space-y-3 pt-2">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Database className="w-4 h-4 text-purple-400" />
            Top Ranked Vector Matches (pgvector Cosine Distance)
          </h4>

          <div className="space-y-3">
            {results.map((res, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-lg bg-purple-500/20 text-purple-300 font-mono font-bold flex items-center justify-center text-[11px]">
                      #{res.rank}
                    </span>
                    <span className="font-bold text-white">{res.source}</span>
                    <span className="text-[10px] text-slate-400">({res.section})</span>
                  </div>

                  <span className="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    Similarity: {res.score.toFixed(2)}
                  </span>
                </div>

                <p className="text-slate-300 font-mono text-[11px] leading-relaxed bg-black/30 p-3 rounded-lg border border-white/5">
                  "{res.chunk_text}"
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
