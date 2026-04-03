"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { screener, type ScreenerSignal } from "@/lib/api";

export default function ScreenerPage() {
  const [tab, setTab] = useState<"screener" | "watchlist">("watchlist");
  const [sectors, setSectors] = useState<{ name: string; count: number }[]>([]);

  // Screener state
  const [selectedSector, setSelectedSector] = useState<string>("Banking");
  const [signals, setSignals] = useState<ScreenerSignal[]>([]);
  const [screenerLoading, setScreenerLoading] = useState(false);
  const [screenerInfo, setScreenerInfo] = useState<string>("");
  const [screenerCountdown, setScreenerCountdown] = useState(60);

  // Watchlist state
  const [watchlistSignals, setWatchlistSignals] = useState<ScreenerSignal[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [watchlistInfo, setWatchlistInfo] = useState<string>("");
  const [watchlistCountdown, setWatchlistCountdown] = useState(15);
  const [addSymbol, setAddSymbol] = useState("");

  // Score filter
  const [minScore, setMinScore] = useState(0);

  // Timers
  const screenerTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const watchlistTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const screenerCdTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const watchlistCdTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    screener.sectors().then((d) => setSectors(d.sectors)).catch(console.error);
  }, []);

  // ============================================================
  // SCREENER: 60-sec refresh
  // ============================================================
  const fetchScreener = useCallback(async () => {
    setScreenerLoading(true);
    try {
      const data = await screener.scan(selectedSector || undefined, 0, 200);
      setSignals(data.signals);
      const src = (data as Record<string, unknown>).source as string || "yahoo";
      const time = new Date().toLocaleTimeString("en-IN");
      setScreenerInfo(`${data.scanned} stocks | ${src} | ${time}`);
    } catch (e) {
      console.error(e);
    } finally {
      setScreenerLoading(false);
      setScreenerCountdown(60);
    }
  }, [selectedSector]);

  // Auto-refresh screener every 60 sec
  useEffect(() => {
    if (tab === "screener") {
      fetchScreener();
      screenerTimer.current = setInterval(fetchScreener, 60000);
      screenerCdTimer.current = setInterval(() => {
        setScreenerCountdown((c) => Math.max(0, c - 1));
      }, 1000);
    }
    return () => {
      if (screenerTimer.current) clearInterval(screenerTimer.current);
      if (screenerCdTimer.current) clearInterval(screenerCdTimer.current);
    };
  }, [tab, selectedSector, fetchScreener]);

  // ============================================================
  // WATCHLIST: 15-sec refresh
  // ============================================================
  const fetchWatchlist = useCallback(async () => {
    setWatchlistLoading(true);
    try {
      const data = await screener.watchlistScan();
      setWatchlistSignals(data.signals);
      const time = new Date().toLocaleTimeString("en-IN");
      setWatchlistInfo(`${data.count} stocks | ${data.source} | ${time}`);
    } catch (e) {
      console.error(e);
    } finally {
      setWatchlistLoading(false);
      setWatchlistCountdown(15);
    }
  }, []);

  // Auto-refresh watchlist every 15 sec
  useEffect(() => {
    if (tab === "watchlist") {
      fetchWatchlist();
      watchlistTimer.current = setInterval(fetchWatchlist, 15000);
      watchlistCdTimer.current = setInterval(() => {
        setWatchlistCountdown((c) => Math.max(0, c - 1));
      }, 1000);
    }
    return () => {
      if (watchlistTimer.current) clearInterval(watchlistTimer.current);
      if (watchlistCdTimer.current) clearInterval(watchlistCdTimer.current);
    };
  }, [tab, fetchWatchlist]);

  const handleAddToWatchlist = async () => {
    if (!addSymbol) return;
    await screener.watchlistAdd(addSymbol.toUpperCase());
    setAddSymbol("");
    fetchWatchlist();
  };

  const handleRemoveFromWatchlist = async (sym: string) => {
    await screener.watchlistRemove(sym);
    fetchWatchlist();
  };

  // Filter signals
  const filteredScreener = minScore > 0 ? signals.filter((s) => s.score >= minScore) : signals;
  const filteredWatchlist = minScore > 0 ? watchlistSignals.filter((s) => s.score >= minScore) : watchlistSignals;

  return (
    <div className="p-6 max-w-7xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">F&O Screener</h1>
        <div className="flex gap-2">
          {[0, 50, 60, 70, 80].map((s) => (
            <button key={s} onClick={() => setMinScore(s)}
              className={`px-2 py-0.5 text-xs rounded ${minScore === s ? "bg-orange-500 text-white" : "bg-gray-800 text-gray-400"}`}>
              {s === 0 ? "All" : `${s}+`}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab("watchlist")}
          className={`px-4 py-2 text-sm rounded-md transition ${
            tab === "watchlist" ? "bg-orange-500 text-white" : "text-gray-400 hover:text-white"
          }`}
        >
          My Watchlist (15s refresh)
        </button>
        <button
          onClick={() => setTab("screener")}
          className={`px-4 py-2 text-sm rounded-md transition ${
            tab === "screener" ? "bg-orange-500 text-white" : "text-gray-400 hover:text-white"
          }`}
        >
          Full Screener (60s refresh)
        </button>
      </div>

      {/* ============================================================
          WATCHLIST TAB
          ============================================================ */}
      {tab === "watchlist" && (
        <>
          {/* Add stock + info bar */}
          <div className="flex items-center justify-between">
            <div className="flex gap-2 items-center">
              <input
                value={addSymbol}
                onChange={(e) => setAddSymbol(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === "Enter" && handleAddToWatchlist()}
                placeholder="Add stock (e.g. TATAMOTORS)"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm w-48"
              />
              <button onClick={handleAddToWatchlist}
                className="px-3 py-1.5 bg-green-600 text-white text-xs rounded-lg hover:bg-green-700">
                Add
              </button>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-500">
              <span>{watchlistInfo}</span>
              <span className={`px-2 py-0.5 rounded ${watchlistLoading ? "bg-orange-500/20 text-orange-400" : "bg-green-500/20 text-green-400"}`}>
                {watchlistLoading ? "Updating..." : `Next: ${watchlistCountdown}s`}
              </span>
            </div>
          </div>

          {/* Watchlist table */}
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
                  <th className="text-center py-2 px-2">Lot</th>
                  <th className="text-center py-2 px-2"></th>
                </tr>
              </thead>
              <tbody>
                {filteredWatchlist.map((sig, i) => (
                  <StockRow key={`${sig.symbol}-${i}`} sig={sig}
                    onRemove={() => handleRemoveFromWatchlist(sig.symbol)} showRemove />
                ))}
                {filteredWatchlist.length === 0 && (
                  <tr><td colSpan={13} className="py-8 text-center text-gray-500">
                    {watchlistLoading ? "Loading watchlist..." : "Add stocks to your watchlist"}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ============================================================
          SCREENER TAB
          ============================================================ */}
      {tab === "screener" && (
        <>
          {/* Sector buttons + info */}
          <div className="flex items-center justify-between">
            <div className="flex gap-1.5 flex-wrap">
              {["Banking", "IT", "Pharma", "Auto", "Energy", "FMCG", "Metal", "Finance", "Infra", "Consumer", "Chemical", "Cement"].map((s) => (
                <button key={s} onClick={() => setSelectedSector(s)}
                  className={`px-2.5 py-1 text-xs rounded-lg transition ${
                    selectedSector === s ? "bg-orange-500 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}>
                  {s}
                </button>
              ))}
              <button onClick={() => setSelectedSector("")}
                className={`px-2.5 py-1 text-xs rounded-lg ${!selectedSector ? "bg-orange-500 text-white" : "bg-gray-800 text-gray-400"}`}>
                All
              </button>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-500">
              <span>{screenerInfo}</span>
              <span className={`px-2 py-0.5 rounded ${screenerLoading ? "bg-orange-500/20 text-orange-400" : "bg-green-500/20 text-green-400"}`}>
                {screenerLoading ? "Scanning..." : `Next: ${screenerCountdown}s`}
              </span>
            </div>
          </div>

          {/* Screener table */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto max-h-[70vh] overflow-y-auto">
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
                {filteredScreener.map((sig, i) => (
                  <StockRow key={`${sig.symbol}-${sig.strategy}-${i}`} sig={sig} />
                ))}
                {filteredScreener.length === 0 && (
                  <tr><td colSpan={12} className="py-8 text-center text-gray-500">
                    {screenerLoading ? "Scanning stocks..." : "No results"}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function StockRow({ sig, onRemove, showRemove = false }: {
  sig: ScreenerSignal; onRemove?: () => void; showRemove?: boolean;
}) {
  return (
    <tr className={`border-b border-gray-800/50 hover:bg-gray-800/30 ${
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
          }`}>{sig.direction.replace("BUY_", "")}</span>
        ) : <span className="text-gray-600">-</span>}
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
      {showRemove ? (
        <td className="py-1.5 px-2 text-center">
          <span className="text-gray-500 font-mono text-[10px] mr-2">{sig.lot_size}</span>
          <button onClick={onRemove} className="text-red-500 hover:text-red-400 text-[10px]">x</button>
        </td>
      ) : (
        <td className="py-1.5 px-2 text-right text-gray-500 font-mono">{sig.lot_size}</td>
      )}
    </tr>
  );
}
