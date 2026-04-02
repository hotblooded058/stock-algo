"use client";

import { useState } from "react";
import { signals, market, type Signal, type WatchlistItem } from "@/lib/api";
import { useEffect } from "react";

export default function SignalsPage() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [selected, setSelected] = useState("");
  const [generated, setGenerated] = useState<Signal[]>([]);
  const [history, setHistory] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"generate" | "history">("generate");

  useEffect(() => {
    market.watchlist().then(setWatchlist).catch(console.error);
    signals.history().then((d) => setHistory(d.signals)).catch(console.error);
  }, []);

  const handleGenerate = async () => {
    if (!selected) return;
    setLoading(true);
    try {
      const data = await signals.generate(selected);
      setGenerated(data.signals);
      // Refresh history
      const hist = await signals.history();
      setHistory(hist.signals);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl space-y-6">
      <h1 className="text-2xl font-bold">Signals</h1>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-800 pb-2">
        <button
          onClick={() => setTab("generate")}
          className={`text-sm pb-2 ${tab === "generate" ? "text-orange-400 border-b-2 border-orange-400" : "text-gray-500"}`}
        >
          Generate
        </button>
        <button
          onClick={() => setTab("history")}
          className={`text-sm pb-2 ${tab === "history" ? "text-orange-400 border-b-2 border-orange-400" : "text-gray-500"}`}
        >
          History ({history.length})
        </button>
      </div>

      {tab === "generate" && (
        <div className="space-y-4">
          <div className="flex gap-3">
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm flex-1"
            >
              <option value="">Select stock...</option>
              {watchlist.map((w) => (
                <option key={w.symbol} value={w.symbol}>{w.name}</option>
              ))}
            </select>
            <button
              onClick={handleGenerate}
              disabled={!selected || loading}
              className="px-6 py-2 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 disabled:opacity-50"
            >
              {loading ? "Generating..." : "Generate Signals"}
            </button>
          </div>

          {generated.length > 0 && (
            <div className="space-y-3">
              {generated.map((sig, i) => (
                <SignalCard key={i} signal={sig} />
              ))}
            </div>
          )}

          {generated.length === 0 && selected && !loading && (
            <p className="text-gray-500 text-sm">No signals generated. Click the button to analyze.</p>
          )}
        </div>
      )}

      {tab === "history" && (
        <div className="space-y-3">
          {history.length > 0 ? (
            history.map((sig, i) => <SignalCard key={i} signal={sig} showTime />)
          ) : (
            <p className="text-gray-500 text-sm">No signal history yet. Generate some signals first.</p>
          )}
        </div>
      )}
    </div>
  );
}

function SignalCard({ signal, showTime = false }: { signal: Signal; showTime?: boolean }) {
  const isCall = signal.direction.includes("CALL");

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-lg text-xs font-bold ${
            isCall ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
          }`}>
            {signal.direction.replace("BUY_", "")}
          </span>
          <span className="font-semibold">{signal.name || signal.symbol}</span>
          <span className="text-xs text-gray-500 capitalize">{signal.strategy}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-bold ${
            signal.strength === "STRONG" ? "text-green-400" :
            signal.strength === "MODERATE" ? "text-orange-400" : "text-gray-400"
          }`}>
            {signal.strength}
          </span>
          <span className="text-lg font-bold">{signal.score}/100</span>
        </div>
      </div>

      {/* Score bar */}
      <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden mb-3">
        <div
          className={`h-full rounded-full transition-all ${
            signal.score >= 80 ? "bg-green-500" : signal.score >= 60 ? "bg-orange-500" : "bg-gray-500"
          }`}
          style={{ width: `${signal.score}%` }}
        />
      </div>

      {/* Reasons */}
      <div className="space-y-1">
        {signal.reasons.map((reason, i) => (
          <p key={i} className="text-xs text-gray-400">
            <span className="text-green-500 mr-1">+</span> {reason}
          </p>
        ))}
      </div>

      {showTime && signal.created_at && (
        <p className="text-xs text-gray-600 mt-2">
          {new Date(signal.created_at).toLocaleString("en-IN")}
        </p>
      )}
    </div>
  );
}
