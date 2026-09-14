"use client";

import { useEffect, useState } from "react";
import { Activity, Database, Sparkles, RefreshCw } from "lucide-react";
import { api, HealthStatus } from "@/lib/api";

export default function Navbar() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch {
      setHealth({
        status: "degraded",
        version: "0.1.0",
        database: "unavailable",
        pgvector: "unavailable",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const isHealthy = health?.status === "healthy";

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-white/10 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-violet-600 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight gradient-text">
              ContentPilot
            </h1>
            <p className="text-xs text-slate-400 font-medium">
              Self-Evaluating Agentic Content System
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs text-slate-300">
            <Database className="w-3.5 h-3.5 text-purple-400" />
            <span>pgvector:</span>
            <span
              className={`font-semibold ${
                health?.pgvector === "ok" ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {health?.pgvector || "checking..."}
            </span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs text-slate-300">
            <Activity className="w-3.5 h-3.5 text-blue-400" />
            <span>System:</span>
            <span className="flex items-center gap-1.5 font-semibold">
              <span
                className={`w-2 h-2 rounded-full ${
                  isHealthy ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
                }`}
              />
              {isHealthy ? "Healthy" : "Degraded"}
            </span>
          </div>

          <button
            onClick={checkHealth}
            disabled={loading}
            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition"
            title="Refresh System Health"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>
    </header>
  );
}
