"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { screener, type ScreenerSignal } from "@/lib/api";

export default function ScreenerPage() {
  const [sectors, setSectors] = useState<{ name: string; count: number }[]>([]);
  const [selectedSector, setSelectedSector] = useState<string>("Banking");
  const [minScore, setMinScore] = useState(0);
  const [signals, setSignals] = useState<ScreenerSignal[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanInfo, setScanInfo] = useState<{
    scanned: number; errors: number; total: number;
    source?: string; cached?: boolean; age?: number; lastUpdated?: string;
  } | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [countdown, setCountdown] = useState(0);
  const refreshInterval = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  const REFRESH_SECONDS = 30;

  useEffect(() => {
    screener.sectors().then((d) => setSectors(d.sectors)).catch(console.error);
  }, []);

  const runScan = useCallback(async (useCache = true) => {
    setLoading(true);
    try {
      const data = await screener.scan(selectedSector || undefined, 0, 200);
      const allSignals = data.signals as (ScreenerSignal & { live?: boolean; cached?: boolean })[];
      setSignals(allSignals);
      setScanInfo({
        scanned: data.scanned,
        errors: data.errors,
        total: data.count,
        source: (data as Record<string, unknown>).source as string,
        cached: (data as Record<string, unknown>).cached as boolean,
        age: (data as Record<string, unknown>).age_seconds as number,
        lastUpdated: (data as Record<string, unknown>).last_updated as string,
      });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setCountdown(REFRESH_SECONDS);
    }
  }, [selectedSector]);

  // Auto-load on page open and sector change
  useEffect(() => {
    runScan(false);
  }, [selectedSector, runScan]);

  // Auto-refresh timer
  useEffect(() => {
    if (autoRefresh) {
      setCountdown(REFRESH_SECONDS);

      countdownInterval.current = setInterval(() => {
        setCountdown((c) => Math.max(0, c - 1));
      }, 1000);

      refreshInterval.current = setInterval(() => {
        runScan(false);
      }, REFRESH_SECONDS * 1000);
    }

    return () => {
      if (refreshInterval.current) clearInterval(refreshInterval.current);
      if (countdownInterval.current) clearInterval(countdownInterval.current);
    };
  }, [autoRefresh, runScan]);

  // Filter by min score
  const filtered = minScore > 0
    ? signals.filter((s) => s.score >= minScore)
    : signals;

  return (
    <div className="p-6 max-w-7xl space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">F&O Screener</h1>
          <p className="text-sm text-gray-500 mt-1">
            {scanInfo?.source === "angelone" ? "Live data via AngelOne" : "Data via Yahoo Finance"} — {signals.length} stocks loaded
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1 text-xs rounded-lg ${autoRefresh ? "bg-green-500/20 text-green-400" : "bg-gray-800 text-gray-500"}`}
          >
            {autoRefresh ? `Auto-refresh: ${countdown}s` : "Auto-refresh OFF"}
          </button>
          <button
            onClick={() => runScan(false)}
            disabled={loading}
            className="px-4 py-1.5 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 disabled:opacity-50"
          >
            {loading ? "Scanning..." : "Refresh Now"}
          </button>
        </div>
      </div>

      {/* Sector buttons */}
      <div className="flex gap-2 flex-wrap">
        {["Banking", "IT", "Pharma", "Auto", "Energy", "FMCG", "Metal", "Finance", "Infra", "Consumer", "Chemical", "Cement"].map((s) => (
          <button
            key={s}
            onClick={() => setSelectedSector(s)}
            className={`px-3 py-1.5 text-xs rounded-lg transition ${
              selectedSector === s ? "bg-orange-500 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            {s} ({sectors.find((x) => x.name === s)?.count || 0})
          </button>
        ))}
        <button
          onClick={() => setSelectedSector("")}
          className={`px-3 py-1.5 text-xs rounded-lg transition ${
            !selectedSector ? "bg-orange-500 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
          }`}
        >
          All
        </button>
      </div>

      {/* Score filter + info bar */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex gap-2 items-center">
          <span className="text-gray-500">Filter:</span>
          {[0, 50, 60, 70, 80].map((s) => (
            <button key={s} onClick={() => setMinScore(s)}
              className={`px-2 py-0.5 rounded ${minScore === s ? "bg-orange-500 text-white" : "bg-gray-800 text-gray-400"}`}>
              {s === 0 ? "All" : `${s}+`}
            </button>
          ))}
        </div>
        <div className="flex gap-4 text-gray-500">
          <span>Showing: <span className="text-white">{filtered.length}</span> / {signals.length}</span>
          {scanInfo?.lastUpdated && (
            <span>Updated: {new Date(scanInfo.lastUpdated).toLocaleTimeString("en-IN")}</span>
          )}
          {scanInfo?.cached && <span className="text-yellow-400">cached</span>}
          {scanInfo?.source && <span className={scanInfo.source === "angelone" ? "text-green-400" : "text-gray-400"}>{scanInfo.source}</span>}
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-gray-900 z-10">
            <tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-2 px-2">Stock</th>
              <th className="text-right py-2 px-2">Price</th>
              <th className="text-right py-2 px-2">Chg%</th>
              <th className="text-center py-2 px-2">Signal</th>
              <th className="text-center py-2 px-2">Score</th>
              <th className="text-center py-2 px-2">Strategy</th>
              <th className="text-center py-2 px-2">RSI</th>
              <th className="text-center py-2 px-2">ADX</th>
              <th className="text-center py-2 px-2">VWAP</th>
              <th className="text-center py-2 px-2">Trend</th>
              <th className="text-center py-2 px-2">Vol</th>
              <th className="text-right py-2 px-2">Lot</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length > 0 ? filtered.map((sig, i) => (
              <tr key={`${sig.symbol}-${sig.strategy}-${i}`}
                className={`border-b border-gray-800/50 hover:bg-gray-800/30 ${
                  sig.score >= 80 ? "bg-green-500/5" : sig.score >= 60 ? "bg-orange-500/5" : ""
                }`}>
                <td className="py-1.5 px-2">
                  <span className="font-medium">{sig.symbol}</span>
                  <span className="text-gray-600 ml-1 text-[10px]">{sig.sector}</span>
                </td>
                <td className="py-1.5 px-2 text-right font-mono">₹{sig.price.toLocaleString("en-IN")}</td>
                <td className={`py-1.5 px-2 text-right font-mono ${sig.change_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {sig.change_pct >= 0 ? "+" : ""}{sig.change_pct.toFixed(2)}%
                </td>
                <td className="py-1.5 px-2 text-center">
                  {sig.direction !== "NONE" ? (
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      sig.direction.includes("CALL") ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                    }`}>
                      {sig.direction.replace("BUY_", "")}
                    </span>
                  ) : (
                    <span className="text-gray-600">-</span>
                  )}
                </td>
                <td className="py-1.5 px-2 text-center">
                  {sig.score > 0 ? (
                    <div className="flex items-center justify-center gap-1">
                      <div className="w-10 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${
                          sig.score >= 80 ? "bg-green-500" : sig.score >= 60 ? "bg-orange-500" : "bg-yellow-500"
                        }`} style={{ width: `${sig.score}%` }} />
                      </div>
                      <span className="font-mono w-5">{sig.score}</span>
                    </div>
                  ) : <span className="text-gray-600">-</span>}
                </td>
                <td className="py-1.5 px-2 text-center text-gray-400 capitalize">{sig.strategy !== "-" ? sig.strategy : ""}</td>
                <td className={`py-1.5 px-2 text-center font-mono ${
                  sig.rsi && sig.rsi > 70 ? "text-red-400" : sig.rsi && sig.rsi < 30 ? "text-green-400" : ""
                }`}>{sig.rsi?.toFixed(0) || "-"}</td>
                <td className={`py-1.5 px-2 text-center font-mono ${
                  sig.adx && sig.adx > 25 ? "text-green-400" : sig.adx && sig.adx < 20 ? "text-red-400" : ""
                }`}>{sig.adx?.toFixed(0) || "-"}</td>
                <td className="py-1.5 px-2 text-center">
                  {sig.above_vwap !== null && sig.above_vwap !== undefined ? (
                    <span className={sig.above_vwap ? "text-green-400" : "text-red-400"}>
                      {sig.above_vwap ? "Above" : "Below"}
                    </span>
                  ) : "-"}
                </td>
                <td className="py-1.5 px-2 text-center">
                  {sig.supertrend ? (
                    <span className={sig.supertrend === "Bullish" ? "text-green-400" : "text-red-400"}>
                      {sig.supertrend === "Bullish" ? "Bull" : "Bear"}
                    </span>
                  ) : "-"}
                </td>
                <td className={`py-1.5 px-2 text-center font-mono ${
                  sig.volume_ratio && sig.volume_ratio > 1.5 ? "text-green-400" :
                  sig.volume_ratio && sig.volume_ratio < 0.8 ? "text-red-400" : ""
                }`}>{sig.volume_ratio?.toFixed(1) || "-"}x</td>
                <td className="py-1.5 px-2 text-right text-gray-500 font-mono">{sig.lot_size}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={12} className="py-8 text-center text-gray-500">
                  {loading ? "Scanning stocks..." : "No results. Try a different sector or lower the score filter."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
