"use client";

import { useEffect, useState } from "react";
import { screener, type ScreenerSignal } from "@/lib/api";

export default function ScreenerPage() {
  const [sectors, setSectors] = useState<{ name: string; count: number }[]>([]);
  const [selectedSector, setSelectedSector] = useState<string>("");
  const [minScore, setMinScore] = useState(50);
  const [signals, setSignals] = useState<ScreenerSignal[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanInfo, setScanInfo] = useState<{ scanned: number; errors: number; total: number } | null>(null);

  useEffect(() => {
    screener.sectors().then((d) => setSectors(d.sectors)).catch(console.error);
  }, []);

  const runScan = async () => {
    setLoading(true);
    setSignals([]);
    try {
      const data = await screener.scan(selectedSector || undefined, minScore, 100);
      setSignals(data.signals);
      setScanInfo({ scanned: data.scanned, errors: data.errors, total: data.count });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // Group signals by sector
  const bySector = signals.reduce<Record<string, ScreenerSignal[]>>((acc, s) => {
    if (!acc[s.sector]) acc[s.sector] = [];
    acc[s.sector].push(s);
    return acc;
  }, {});

  return (
    <div className="p-6 max-w-7xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">F&O Screener</h1>
        <p className="text-sm text-gray-500 mt-1">
          Scan 200+ F&O stocks for trading signals with live data
        </p>
      </div>

      {/* Controls */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex gap-3 flex-wrap items-end">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Sector</label>
            <select
              value={selectedSector}
              onChange={(e) => setSelectedSector(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">All Sectors ({sectors.reduce((a, s) => a + s.count, 0)} stocks)</option>
              {sectors.map((s) => (
                <option key={s.name} value={s.name}>{s.name} ({s.count})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Min Score</label>
            <select
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            >
              <option value={40}>40+ (All signals)</option>
              <option value={50}>50+ (Moderate+)</option>
              <option value={60}>60+ (Strong signals)</option>
              <option value={70}>70+ (Very strong only)</option>
            </select>
          </div>
          <button
            onClick={runScan}
            disabled={loading}
            className="px-6 py-2 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 disabled:opacity-50"
          >
            {loading ? "Scanning..." : `Scan ${selectedSector || "All"} Stocks`}
          </button>
          {loading && (
            <p className="text-xs text-gray-500 self-center">This may take 1-2 minutes for all stocks...</p>
          )}
        </div>

        {/* Quick sector buttons */}
        <div className="flex gap-2 mt-3 flex-wrap">
          {["Banking", "IT", "Pharma", "Auto", "Energy", "FMCG", "Metal", "Finance"].map((s) => (
            <button
              key={s}
              onClick={() => { setSelectedSector(s); }}
              className={`px-3 py-1 text-xs rounded-lg ${
                selectedSector === s ? "bg-orange-500 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {s}
            </button>
          ))}
          <button
            onClick={() => setSelectedSector("")}
            className={`px-3 py-1 text-xs rounded-lg ${
              !selectedSector ? "bg-orange-500 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            All
          </button>
        </div>
      </div>

      {/* Scan Info */}
      {scanInfo && (
        <div className="flex gap-4 text-xs text-gray-500">
          <span>Found: <span className="text-white font-bold">{scanInfo.total}</span> signals</span>
          <span>Scanned: {scanInfo.scanned} stocks</span>
          {scanInfo.errors > 0 && <span className="text-red-400">{scanInfo.errors} errors</span>}
        </div>
      )}

      {/* Results Table */}
      {signals.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800 text-xs">
                <th className="text-left py-2 px-3">Stock</th>
                <th className="text-left py-2 px-3">Sector</th>
                <th className="text-right py-2 px-3">Price</th>
                <th className="text-right py-2 px-3">Chg%</th>
                <th className="text-center py-2 px-3">Signal</th>
                <th className="text-center py-2 px-3">Score</th>
                <th className="text-center py-2 px-3">Strength</th>
                <th className="text-center py-2 px-3">Strategy</th>
                <th className="text-center py-2 px-3">RSI</th>
                <th className="text-center py-2 px-3">ADX</th>
                <th className="text-center py-2 px-3">VWAP</th>
                <th className="text-center py-2 px-3">Trend</th>
                <th className="text-center py-2 px-3">Vol</th>
                <th className="text-right py-2 px-3">Lot</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((sig, i) => (
                <tr key={`${sig.symbol}-${sig.strategy}-${i}`} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 px-3 font-medium">{sig.symbol}</td>
                  <td className="py-2 px-3 text-gray-400 text-xs">{sig.sector}</td>
                  <td className="py-2 px-3 text-right font-mono">₹{sig.price.toLocaleString("en-IN")}</td>
                  <td className={`py-2 px-3 text-right font-mono ${sig.change_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {sig.change_pct >= 0 ? "+" : ""}{sig.change_pct.toFixed(2)}%
                  </td>
                  <td className="py-2 px-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                      sig.direction.includes("CALL") ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                    }`}>
                      {sig.direction.replace("BUY_", "")}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <div className="w-12 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            sig.score >= 80 ? "bg-green-500" : sig.score >= 60 ? "bg-orange-500" : "bg-yellow-500"
                          }`}
                          style={{ width: `${sig.score}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono">{sig.score}</span>
                    </div>
                  </td>
                  <td className="py-2 px-3 text-center">
                    <span className={`text-xs font-medium ${
                      sig.strength === "STRONG" ? "text-green-400" :
                      sig.strength === "MODERATE" ? "text-orange-400" : "text-yellow-400"
                    }`}>
                      {sig.strength}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-center text-xs text-gray-400 capitalize">{sig.strategy}</td>
                  <td className={`py-2 px-3 text-center font-mono text-xs ${
                    sig.rsi && sig.rsi > 70 ? "text-red-400" :
                    sig.rsi && sig.rsi < 30 ? "text-green-400" : ""
                  }`}>
                    {sig.rsi?.toFixed(0) || "-"}
                  </td>
                  <td className={`py-2 px-3 text-center font-mono text-xs ${
                    sig.adx && sig.adx > 25 ? "text-green-400" :
                    sig.adx && sig.adx < 20 ? "text-red-400" : ""
                  }`}>
                    {sig.adx?.toFixed(0) || "-"}
                  </td>
                  <td className="py-2 px-3 text-center">
                    {sig.above_vwap !== null && (
                      <span className={`text-xs ${sig.above_vwap ? "text-green-400" : "text-red-400"}`}>
                        {sig.above_vwap ? "Above" : "Below"}
                      </span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-center">
                    {sig.supertrend && (
                      <span className={`text-xs ${sig.supertrend === "Bullish" ? "text-green-400" : "text-red-400"}`}>
                        {sig.supertrend === "Bullish" ? "Bull" : "Bear"}
                      </span>
                    )}
                  </td>
                  <td className={`py-2 px-3 text-center font-mono text-xs ${
                    sig.volume_ratio && sig.volume_ratio > 1.5 ? "text-green-400" :
                    sig.volume_ratio && sig.volume_ratio < 0.8 ? "text-red-400" : ""
                  }`}>
                    {sig.volume_ratio?.toFixed(1) || "-"}x
                  </td>
                  <td className="py-2 px-3 text-right text-xs text-gray-500 font-mono">{sig.lot_size}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty state */}
      {!loading && signals.length === 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
          <p className="text-lg mb-2">Select a sector and click Scan</p>
          <p className="text-sm">
            Tip: Scan by sector for faster results. &quot;All Stocks&quot; takes 1-2 minutes.
          </p>
        </div>
      )}
    </div>
  );
}
