"use client";

import { useState, useEffect } from "react";
import { 
  Zap, 
  Database, 
  Brain, 
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  Tag,
  MessageSquare,
  TrendingUp
} from "lucide-react";
import { createTicket, getTickets, correctTicket, getHealth, getAnalytics } from "@/lib/api";
import type { 
  Ticket, 
  ClassificationResult, 
  TicketCategory, 
  HealthStatus,
  AnalyticsOverview 
} from "@/types";

const CATEGORIES: TicketCategory[] = [
  "Product Issue",
  "Software Issue",
  "Network Issue",
  "Battery Issue",
  "General Question",
];

const CATEGORY_COLORS: Record<string, string> = {
  "Product Issue": "#f59e0b",
  "Software Issue": "#3b82f6",
  "Network Issue": "#10b981",
  "Battery Issue": "#ec4899",
  "General Question": "#a855f7",
};

interface LogEntry {
  time: string;
  type: "info" | "success" | "error" | "warn" | "system";
  message: string;
}

export default function Home() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClassificationResult | null>(null);
  const [currentTicketId, setCurrentTicketId] = useState<string | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([
    { time: getTime(), type: "system", message: "Taskio Pro v2.0.0 initialized" },
    { time: getTime(), type: "info", message: "Connecting to services..." },
  ]);

  function getTime() {
    return new Date().toLocaleTimeString("en-US", { hour12: false });
  }

  function addLog(type: LogEntry["type"], message: string) {
    setLogs((prev) => [...prev.slice(-12), { time: getTime(), type, message }]);
  }

  useEffect(() => {
    async function init() {
      try {
        const [healthData, analyticsData, ticketsData] = await Promise.all([
          getHealth(),
          getAnalytics(),
          getTickets(1, 5),
        ]);
        
        setHealth(healthData);
        setAnalytics(analyticsData);
        setTickets(ticketsData.tickets);
        
        addLog("success", `PostgreSQL: connected`);
        addLog("success", `ChromaDB: ${analyticsData.vector_store_count} embeddings`);
        addLog("success", `LangChain agent: ready`);
        addLog("info", "System ready - awaiting input");
      } catch (err) {
        addLog("error", "Failed to connect to backend");
      }
    }
    init();
  }, []);

  async function handleClassify() {
    if (description.length < 10) {
      addLog("error", "Description too short (min 10 chars)");
      return;
    }

    setLoading(true);
    addLog("info", `Processing: "${title || description.slice(0, 30)}..."`);

    try {
      const response = await createTicket({ title, description });
      
      setResult(response.classification);
      setCurrentTicketId(response.ticket.id);
      setTickets((prev) => [response.ticket, ...prev.slice(0, 4)]);
      
      const cat = response.classification.category;
      const conf = Math.round(response.classification.confidence * 100);
      const latency = Math.round(response.classification.latency_ms);
      
      addLog("success", `Classified: ${cat} (${conf}% confidence)`);
      addLog("info", `Latency: ${latency}ms | RAG: ${response.classification.rag_used ? "yes" : "no"} | Cached: ${response.classification.cached ? "yes" : "no"}`);
      
      if (response.classification.similar_tickets.length > 0) {
        addLog("info", `Found ${response.classification.similar_tickets.length} similar tickets via vector search`);
      }
    } catch (err) {
      addLog("error", `Classification failed: ${err}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleCorrect(category: TicketCategory) {
    if (!currentTicketId) {
      addLog("warn", "No ticket selected for correction");
      return;
    }

    try {
      await correctTicket(currentTicketId, { corrected_category: category });
      addLog("info", `Label corrected → ${category}`);
      setResult((prev) => prev ? { ...prev, category } : null);
    } catch (err) {
      addLog("error", "Correction failed");
    }
  }

  const logColors: Record<string, string> = {
    system: "#6b7280",
    info: "#60a5fa",
    success: "#34d399",
    error: "#f87171",
    warn: "#fbbf24",
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-zinc-300 font-mono text-sm p-4">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Header */}
        <header className="flex items-center justify-between p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <div className="w-3 h-3 rounded-full bg-green-500" />
            </div>
            <span className="text-zinc-500 text-xs">taskio-pro@classifier:~</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-zinc-500">
            <span className="flex items-center gap-1.5">
              <Brain className="w-3.5 h-3.5" />
              LangChain + Gemini
            </span>
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5" />
              ChromaDB (RAG)
            </span>
            <span className={`flex items-center gap-1.5 ${health?.status === "healthy" ? "text-green-400" : "text-yellow-400"}`}>
              <Activity className="w-3.5 h-3.5" />
              {health?.status || "connecting..."}
            </span>
          </div>
        </header>

        {/* Stats Row */}
        <div className="grid grid-cols-5 gap-3">
          {[
            { label: "accuracy", value: `${analytics?.accuracy.accuracy_percentage || 0}%`, color: "#10b981" },
            { label: "processed", value: analytics?.total_tickets || 0, color: "#3b82f6" },
            { label: "cache_hit", value: `${analytics?.cache_hit_rate || 0}%`, color: "#a855f7" },
            { label: "vectors", value: analytics?.vector_store_count || 0, color: "#f59e0b" },
            { label: "confidence", value: `${analytics?.avg_confidence || 0}%`, color: "#ec4899" },
          ].map((stat) => (
            <div key={stat.label} className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
              <div className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1">{stat.label}</div>
              <div className="text-xl font-bold" style={{ color: stat.color }}>{stat.value}</div>
            </div>
          ))}
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-2 gap-4">
          {/* Input Panel */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-zinc-800 text-xs text-zinc-500 flex items-center gap-2">
              <span className="text-blue-400">❯</span> new_ticket.input
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5">
                  --title <span className="text-zinc-700">(optional)</span>
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="ticket title..."
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-2 text-zinc-300 placeholder-zinc-700 focus:outline-none focus:border-zinc-600"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5">
                  --description <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="describe the issue..."
                  rows={4}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-2 text-zinc-300 placeholder-zinc-700 focus:outline-none focus:border-zinc-600 resize-none"
                />
              </div>
              <button
                onClick={handleClassify}
                disabled={loading}
                className={`w-full py-2.5 rounded font-medium text-xs transition-all ${
                  loading
                    ? "bg-zinc-800 text-zinc-600 cursor-not-allowed"
                    : "bg-zinc-100 text-zinc-900 hover:bg-white"
                }`}
              >
                {loading ? "⏳ processing..." : "→ classify --execute"}
              </button>

              {/* Result */}
              {result && (
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded space-y-3">
                  <div className="text-[10px] uppercase tracking-wider text-zinc-600">output:</div>
                  <div className="flex items-center justify-between">
                    <span
                      className="px-2.5 py-1 rounded text-xs font-medium"
                      style={{
                        backgroundColor: `${CATEGORY_COLORS[result.category]}20`,
                        color: CATEGORY_COLORS[result.category],
                      }}
                    >
                      {result.category}
                    </span>
                    <span className="text-zinc-500 text-xs">
                      confidence: {Math.round(result.confidence * 100)}%
                    </span>
                  </div>
                  <p className="text-xs text-zinc-500 leading-relaxed">{result.reasoning}</p>
                  {result.key_indicators.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {result.key_indicators.map((indicator, i) => (
                        <span key={i} className="text-[10px] px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-400">
                          {indicator}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="text-[10px] text-zinc-600">
                    latency: {Math.round(result.latency_ms)}ms | rag: {result.rag_used ? "✓" : "✗"} | cached: {result.cached ? "✓" : "✗"}
                  </div>

                  {/* Correction Buttons */}
                  <div className="pt-3 border-t border-zinc-800">
                    <div className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">correct label:</div>
                    <div className="flex flex-wrap gap-1.5">
                      {CATEGORIES.map((cat) => (
                        <button
                          key={cat}
                          onClick={() => handleCorrect(cat)}
                          className={`px-2 py-1 text-[10px] rounded border transition-all ${
                            result.category === cat
                              ? "bg-zinc-100 text-zinc-900 border-zinc-100"
                              : "bg-transparent text-zinc-500 border-zinc-800 hover:border-zinc-600"
                          }`}
                        >
                          {cat}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column */}
          <div className="space-y-4">
            {/* Recent Tickets */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
              <div className="px-3 py-2 border-b border-zinc-800 text-xs text-zinc-500 flex items-center gap-2">
                <span className="text-green-400">❯</span> recent_tickets.log
              </div>
              <div className="divide-y divide-zinc-800/50 max-h-[220px] overflow-y-auto">
                {tickets.map((ticket, i) => (
                  <div key={ticket.id} className="p-3 hover:bg-zinc-800/30 transition-colors">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <span className="text-zinc-400 text-xs truncate flex-1">{ticket.title}</span>
                      <span
                        className="text-[9px] px-1.5 py-0.5 rounded shrink-0"
                        style={{
                          backgroundColor: `${CATEGORY_COLORS[ticket.predicted_category || "General Question"]}20`,
                          color: CATEGORY_COLORS[ticket.predicted_category || "General Question"],
                        }}
                      >
                        {ticket.predicted_category}
                      </span>
                    </div>
                    <div className="text-[10px] text-zinc-600 truncate">{ticket.description}</div>
                  </div>
                ))}
                {tickets.length === 0 && (
                  <div className="p-6 text-center text-zinc-600 text-xs">No tickets yet</div>
                )}
              </div>
            </div>

            {/* System Logs */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
              <div className="px-3 py-2 border-b border-zinc-800 text-xs text-zinc-500 flex items-center gap-2">
                <span className="text-yellow-400">❯</span> system.log
              </div>
              <div className="p-3 space-y-1 max-h-[180px] overflow-y-auto font-mono text-[11px]">
                {logs.map((log, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-zinc-700 shrink-0">{log.time}</span>
                    <span style={{ color: logColors[log.type] }}>[{log.type.toUpperCase()}]</span>
                    <span className="text-zinc-400">{log.message}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="flex items-center justify-between p-3 bg-zinc-900 border border-zinc-800 rounded-lg text-[10px] text-zinc-600">
          <span>taskio-pro v2.0.0 | fastapi + langchain + chromadb + postgresql</span>
          <span>Next.js + TypeScript | © 2024</span>
        </footer>
      </div>
    </div>
  );
}
