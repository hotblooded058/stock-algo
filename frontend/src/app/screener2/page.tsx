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

  // Trade plan modal
  const [planSymbol, setPlanSymbol] = useState<string | null>(null);
  const [plan, setPlan] = useState<Record<string, unknown> | null>(null);
  const [planLoading, setPlanLoading] = useState(false);

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

  // Trade plan
  const openTradePlan = async (symbol: string) => {
    setPlanSymbol(symbol);
    setPlan(null);
    setPlanLoading(true);
    try {
      const data = await screener.tradePlan(symbol);
      setPlan(data);
    } catch (e) {
      console.error(e);
    } finally {
      setPlanLoading(false);
    }
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
                    onClick={() => openTradePlan(sig.symbol)}
                    selected={planSymbol === sig.symbol}
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
                  <StockRow key={`${sig.symbol}-${sig.strategy}-${i}`} sig={sig}
                    onClick={() => openTradePlan(sig.symbol)}
                    selected={planSymbol === sig.symbol} />
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

      {/* TRADE PLAN PANEL */}
      {planSymbol && (
        <TradePlanPanel
          symbol={planSymbol}
          plan={plan}
          loading={planLoading}
          onClose={() => { setPlanSymbol(null); setPlan(null); }}
        />
      )}
    </div>
  );
}

// ============================================================
// TRADE PLAN PANEL
// ============================================================

function TradePlanPanel({ symbol, plan, loading, onClose }: {
  symbol: string; plan: Record<string, unknown> | null; loading: boolean; onClose: () => void;
}) {
  if (loading) {
    return (
      <div className="bg-gray-900 border border-orange-500/30 rounded-xl p-6 mt-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold">Generating trade plan for {symbol}...</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white">Close</button>
        </div>
        <div className="mt-4 text-gray-500 animate-pulse">Analyzing indicators, computing Greeks, building plan...</div>
      </div>
    );
  }

  if (!plan) return null;

  const verdict = plan.verdict as string || "NO TRADE";
  const confidence = plan.confidence as number || 0;
  const confLabel = plan.confidence_label as string || "";
  const isCall = verdict.includes("CALL");
  const isPut = verdict.includes("PUT");
  const noTrade = verdict === "NO TRADE";

  const mkt = plan.market as Record<string, unknown> || {};
  const opt = plan.option as Record<string, unknown> || {};
  const tradePlan = plan.plan as Record<string, unknown> || {};
  const checklist = plan.checklist as { check: string; passed: boolean; critical: boolean }[] || [];
  const warnings = plan.warnings as string[] || [];
  const exitRules = plan.exit_rules as string[] || [];
  const avoidIf = plan.avoid_if as string[] || [];
  const reasons = plan.reasons as string[] || [];

  return (
    <div className="bg-gray-900 border border-orange-500/30 rounded-xl p-5 mt-4 space-y-4">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold">{symbol} Trade Plan</h2>
            <span className={`px-3 py-1 rounded-lg text-sm font-bold ${
              isCall ? "bg-green-500/20 text-green-400" : isPut ? "bg-red-500/20 text-red-400" : "bg-gray-700 text-gray-400"
            }`}>{verdict}</span>
            <span className={`px-2 py-0.5 rounded text-xs ${
              confLabel === "HIGH" ? "bg-green-500/20 text-green-400" :
              confLabel === "MEDIUM" ? "bg-orange-500/20 text-orange-400" : "bg-red-500/20 text-red-400"
            }`}>{confidence}% {confLabel}</span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {plan.sector as string} | Spot: ₹{(plan.spot_price as number)?.toLocaleString("en-IN")} |
            {mkt.regime as string} | {mkt.direction as string}
          </p>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-white text-lg">x</button>
      </div>

      {noTrade ? (
        /* NO TRADE view */
        <div className="space-y-3">
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-orange-400 font-semibold mb-2">Why no trade?</p>
            {(plan.reasons_to_skip as string[] || []).map((r, i) => (
              <p key={i} className="text-sm text-gray-400">- {r}</p>
            ))}
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-blue-400 font-semibold mb-2">Wait for:</p>
            {(plan.wait_for as string[] || []).map((r, i) => (
              <p key={i} className="text-sm text-gray-400">- {r}</p>
            ))}
          </div>
        </div>
      ) : (
        /* TRADE PLAN view */
        <div className="space-y-4">
          {/* Signal Reasons */}
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-xs text-gray-500 mb-2">WHY THIS TRADE (Score: {plan.signal_score as number}, Strategy: {plan.strategy as string})</p>
            <div className="space-y-1">
              {reasons.map((r, i) => (
                <p key={i} className="text-sm text-gray-300">
                  <span className="text-green-400 mr-1">+</span> {r}
                </p>
              ))}
            </div>
          </div>

          {/* Option + Trade Plan */}
          <div className="grid md:grid-cols-2 gap-4">
            {/* Option details */}
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="text-xs text-gray-500 mb-3">RECOMMENDED OPTION</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-gray-500">Strike:</span> <span className="font-bold">{symbol} {opt.strike as number} {opt.type as string}</span></div>
                <div><span className="text-gray-500">Expiry:</span> <span className="font-mono">{opt.expiry as string} ({opt.dte as number} DTE)</span></div>
                <div><span className="text-gray-500">Premium:</span> <span className="font-bold text-orange-400 font-mono">₹{opt.estimated_premium as number}</span></div>
                <div><span className="text-gray-500">Delta:</span> <span className="font-mono">{(opt.delta as number)?.toFixed(3)}</span></div>
                <div><span className="text-gray-500">IV:</span> <span className="font-mono">{(opt.iv as number)?.toFixed(1)}%</span></div>
                <div><span className="text-gray-500">Moneyness:</span> {opt.moneyness as string}</div>
              </div>
            </div>

            {/* P&L Plan */}
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="text-xs text-gray-500 mb-3">TRADE PLAN</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-gray-500">Entry:</span> <span className="font-bold font-mono">₹{tradePlan.entry_premium as number}</span></div>
                <div><span className="text-gray-500">Qty:</span> <span className="font-bold">{tradePlan.quantity as number} ({tradePlan.lot_size as number}/lot)</span></div>
                <div><span className="text-gray-500">Stop Loss:</span> <span className="text-red-400 font-bold font-mono">₹{tradePlan.stop_loss as number}</span></div>
                <div><span className="text-gray-500">Max Loss:</span> <span className="text-red-400 font-mono">₹{(tradePlan.max_loss as number)?.toLocaleString("en-IN")}</span></div>
                <div><span className="text-gray-500">Target 1:</span> <span className="text-green-400 font-bold font-mono">₹{tradePlan.target_1 as number}</span></div>
                <div><span className="text-gray-500">T1 Profit:</span> <span className="text-green-400 font-mono">₹{(tradePlan.target_1_profit as number)?.toLocaleString("en-IN")}</span></div>
                <div><span className="text-gray-500">Target 2:</span> <span className="text-green-400 font-mono">₹{tradePlan.target_2 as number}</span></div>
                <div><span className="text-gray-500">R:R:</span> <span className="font-bold">{tradePlan.risk_reward as number}x</span></div>
                <div><span className="text-gray-500">Total Cost:</span> <span className="font-mono">₹{(tradePlan.total_cost as number)?.toLocaleString("en-IN")}</span></div>
                <div><span className="text-gray-500">Risk:</span> <span className="font-mono">{tradePlan.risk_pct_of_capital as number}% of capital</span></div>
              </div>
            </div>
          </div>

          {/* Checklist */}
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-xs text-gray-500 mb-2">PRE-TRADE CHECKLIST</p>
            <div className="grid md:grid-cols-2 gap-1">
              {checklist.map((c, i) => (
                <div key={i} className={`flex items-center gap-2 text-sm ${c.critical ? "font-medium" : ""}`}>
                  <span className={c.passed ? "text-green-400" : "text-red-400"}>{c.passed ? "PASS" : "FAIL"}</span>
                  <span className={c.passed ? "text-gray-300" : "text-gray-500"}>{c.check}</span>
                  {c.critical && !c.passed && <span className="text-red-400 text-[10px]">CRITICAL</span>}
                </div>
              ))}
            </div>
          </div>

          {/* Warnings */}
          {warnings.length > 0 && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
              <p className="text-xs text-red-400 mb-2">WARNINGS</p>
              {warnings.map((w, i) => (
                <p key={i} className="text-sm text-red-300">- {w}</p>
              ))}
            </div>
          )}

          {/* Exit Rules */}
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-xs text-gray-500 mb-2">EXIT RULES</p>
            {exitRules.map((r, i) => (
              <p key={i} className="text-sm text-gray-400">
                <span className="text-orange-400 mr-1">{i + 1}.</span> {r}
              </p>
            ))}
          </div>

          {/* Avoid conditions */}
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-xs text-gray-500 mb-2">DO NOT TRADE IF</p>
            {avoidIf.map((a, i) => (
              <p key={i} className="text-sm text-gray-500">- {a}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StockRow({ sig, onRemove, showRemove = false, onClick, selected = false }: {
  sig: ScreenerSignal; onRemove?: () => void; showRemove?: boolean;
  onClick?: () => void; selected?: boolean;
}) {
  return (
    <tr onClick={onClick} className={`border-b border-gray-800/50 cursor-pointer transition ${
      selected ? "bg-orange-500/10 ring-1 ring-orange-500/30" :
      sig.score >= 80 ? "bg-green-500/5 hover:bg-green-500/10" :
      sig.score >= 60 ? "bg-orange-500/5 hover:bg-orange-500/10" : "hover:bg-gray-800/30"
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
