"use client";

import { useEffect, useState } from "react";
import { paper, type PaperPosition, type PaperStats } from "@/lib/api";

export default function PaperTradingPage() {
  const [positions, setPositions] = useState<PaperPosition[]>([]);
  const [history, setHistory] = useState<PaperPosition[]>([]);
  const [stats, setStats] = useState<PaperStats | null>(null);
  const [tab, setTab] = useState<"enter" | "positions" | "history" | "stats">("enter");
  const [loading, setLoading] = useState(false);

  // Entry form
  const [symbol, setSymbol] = useState("");
  const [direction, setDirection] = useState("BUY_CALL");
  const [premium, setPremium] = useState<number>(0);
  const [quantity, setQuantity] = useState<number>(0);
  const [sl, setSl] = useState<number>(0);
  const [target, setTarget] = useState<number>(0);
  const [instrument, setInstrument] = useState("");
  const [notes, setNotes] = useState("");
  const [entryResult, setEntryResult] = useState<string>("");

  // Exit form
  const [exitPrice, setExitPrice] = useState<number>(0);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [p, h, s] = await Promise.all([
        paper.positions(),
        paper.history(),
        paper.stats(),
      ]);
      setPositions(p.positions);
      setHistory(h.trades);
      setStats(s);
    } catch (e) {
      console.error(e);
    }
  };

  const handleEnter = async () => {
    if (!symbol || !premium) {
      setEntryResult("Enter symbol and premium");
      return;
    }
    setLoading(true);
    try {
      const result = await paper.enter({
        symbol,
        direction,
        entry_premium: premium,
        quantity: quantity || undefined,
        stop_loss: sl || undefined,
        target_1: target || undefined,
        instrument: instrument || undefined,
        notes: notes || undefined,
      });
      setEntryResult(result.message || "Trade entered!");
      loadData();
      // Reset form
      setPremium(0); setQuantity(0); setSl(0); setTarget(0);
      setInstrument(""); setNotes("");
    } catch (e) {
      setEntryResult("Error entering trade");
    } finally {
      setLoading(false);
    }
  };

  const handleExit = async (tradeId: number, price: number, reason: string) => {
    try {
      const result = await paper.exit(tradeId, price, reason);
      setEntryResult(result.message);
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  // Auto-calculate SL and target when premium changes
  useEffect(() => {
    if (premium > 0) {
      if (!sl) setSl(Math.round(premium * 0.7 * 100) / 100);
      if (!target) setTarget(Math.round(premium * 1.4 * 100) / 100);
    }
  }, [premium, sl, target]);

  return (
    <div className="p-6 max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Paper Trading</h1>
        <p className="text-sm text-gray-500 mt-1">Practice with real prices, zero risk</p>
      </div>

      {/* Stats Banner */}
      {stats && (
        <div className={`rounded-xl p-4 border ${stats.ready_for_live ? "bg-green-500/10 border-green-500/30" : "bg-gray-900 border-gray-800"}`}>
          <div className="flex items-center justify-between">
            <div className="flex gap-6 text-sm">
              <span>Trades: <b>{stats.closed_trades}</b>/30</span>
              <span>WR: <b className={stats.win_rate >= 50 ? "text-green-400" : "text-red-400"}>{stats.win_rate}%</b></span>
              <span>P&L: <b className={stats.total_pnl >= 0 ? "text-green-400" : "text-red-400"}>₹{stats.total_pnl.toLocaleString("en-IN")}</b></span>
              <span>PF: <b>{stats.profit_factor}</b></span>
              <span>Open: <b>{stats.open_trades}</b></span>
            </div>
            <span className={`text-xs px-3 py-1 rounded-full ${stats.ready_for_live ? "bg-green-500/20 text-green-400" : "bg-orange-500/20 text-orange-400"}`}>
              {stats.message}
            </span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-800 pb-2">
        {(["enter", "positions", "history", "stats"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`text-sm pb-2 capitalize ${tab === t ? "text-orange-400 border-b-2 border-orange-400" : "text-gray-500"}`}
          >
            {t === "enter" ? "New Trade" : t === "positions" ? `Positions (${positions.length})` : t}
          </button>
        ))}
      </div>

      {/* ENTER TAB */}
      {tab === "enter" && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h3 className="font-semibold">Enter Paper Trade</h3>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Symbol</label>
              <input
                value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="e.g. NIFTY, SBIN"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Direction</label>
              <select value={direction} onChange={(e) => setDirection(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full">
                <option value="BUY_CALL">BUY CALL</option>
                <option value="BUY_PUT">BUY PUT</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Premium (entry price)</label>
              <input type="number" value={premium || ""} onChange={(e) => { setPremium(Number(e.target.value)); setSl(0); setTarget(0); }}
                placeholder="e.g. 150"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Quantity (0 = auto)</label>
              <input type="number" value={quantity || ""} onChange={(e) => setQuantity(Number(e.target.value))}
                placeholder="Auto from risk"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Stop Loss</label>
              <input type="number" value={sl || ""} onChange={(e) => setSl(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Target</label>
              <input type="number" value={target || ""} onChange={(e) => setTarget(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Instrument (optional)</label>
              <input value={instrument} onChange={(e) => setInstrument(e.target.value)}
                placeholder="e.g. NIFTY26APR22500CE"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Notes</label>
              <input value={notes} onChange={(e) => setNotes(e.target.value)}
                placeholder="Why this trade?"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full"
              />
            </div>
          </div>

          {premium > 0 && (
            <div className="bg-gray-800 rounded-lg p-3 text-xs grid grid-cols-4 gap-3">
              <div>SL: <span className="text-red-400 font-mono">₹{sl.toFixed(2)}</span> ({((1 - sl/premium) * 100).toFixed(0)}% loss)</div>
              <div>Target: <span className="text-green-400 font-mono">₹{target.toFixed(2)}</span> ({((target/premium - 1) * 100).toFixed(0)}% profit)</div>
              <div>Risk/unit: <span className="text-red-400 font-mono">₹{(premium - sl).toFixed(2)}</span></div>
              <div>Reward/unit: <span className="text-green-400 font-mono">₹{(target - premium).toFixed(2)}</span></div>
            </div>
          )}

          <div className="flex gap-3 items-center">
            <button onClick={handleEnter} disabled={loading || !symbol || !premium}
              className="px-6 py-2 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 disabled:opacity-50">
              {loading ? "Entering..." : "Enter Paper Trade"}
            </button>
            {entryResult && (
              <span className={`text-sm ${entryResult.includes("Error") ? "text-red-400" : "text-green-400"}`}>
                {entryResult}
              </span>
            )}
          </div>
        </div>
      )}

      {/* POSITIONS TAB */}
      {tab === "positions" && (
        <div className="space-y-3">
          {positions.length > 0 ? positions.map((pos) => (
            <div key={pos.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    pos.direction.includes("CALL") ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                  }`}>{pos.direction.replace("BUY_", "")}</span>
                  <span className="font-bold">{pos.symbol}</span>
                  <span className="text-xs text-gray-500">{pos.instrument}</span>
                  <span className="text-xs text-gray-500">x{pos.quantity}</span>
                </div>
                <span className="text-xs text-gray-500">{pos.broker_order_id}</span>
              </div>

              <div className="grid grid-cols-4 gap-3 text-sm mb-3">
                <div>
                  <p className="text-[10px] text-gray-500">Entry</p>
                  <p className="font-mono">₹{pos.entry_price}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500">Stop Loss</p>
                  <p className="font-mono text-red-400">₹{pos.stop_loss}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500">Target</p>
                  <p className="font-mono text-green-400">₹{pos.target_1}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500">Entry Time</p>
                  <p className="text-xs">{new Date(pos.entry_time).toLocaleString("en-IN")}</p>
                </div>
              </div>

              {/* Exit controls */}
              <div className="flex gap-2 items-center border-t border-gray-800 pt-3">
                <input type="number" placeholder="Exit price" value={exitPrice || ""}
                  onChange={(e) => setExitPrice(Number(e.target.value))}
                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm w-24"
                />
                <button onClick={() => handleExit(pos.id, exitPrice, "manual")}
                  className="px-3 py-1 bg-gray-700 text-white text-xs rounded hover:bg-gray-600">
                  Exit Manual
                </button>
                <button onClick={() => handleExit(pos.id, pos.stop_loss || 0, "stop_loss")}
                  className="px-3 py-1 bg-red-600/80 text-white text-xs rounded hover:bg-red-600">
                  Hit SL (₹{pos.stop_loss})
                </button>
                <button onClick={() => handleExit(pos.id, pos.target_1 || 0, "target_1")}
                  className="px-3 py-1 bg-green-600/80 text-white text-xs rounded hover:bg-green-600">
                  Hit Target (₹{pos.target_1})
                </button>
              </div>
            </div>
          )) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
              No open positions. Enter a paper trade to start.
            </div>
          )}
        </div>
      )}

      {/* HISTORY TAB */}
      {tab === "history" && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
          {history.filter(h => h.status !== "OPEN").length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800 text-xs">
                  <th className="text-left py-2 px-3">Date</th>
                  <th className="text-left py-2 px-3">Symbol</th>
                  <th className="text-center py-2 px-3">Dir</th>
                  <th className="text-right py-2 px-3">Entry</th>
                  <th className="text-right py-2 px-3">Exit</th>
                  <th className="text-right py-2 px-3">Qty</th>
                  <th className="text-right py-2 px-3">P&L</th>
                  <th className="text-center py-2 px-3">Reason</th>
                  <th className="text-center py-2 px-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {history.filter(h => h.status !== "OPEN").map((t) => (
                  <tr key={t.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-2 px-3 text-xs text-gray-400">{t.entry_time?.split("T")[0]}</td>
                    <td className="py-2 px-3 font-medium">{t.symbol}</td>
                    <td className="py-2 px-3 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                        t.direction.includes("CALL") ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                      }`}>{t.direction.replace("BUY_", "")}</span>
                    </td>
                    <td className="py-2 px-3 text-right font-mono">₹{t.entry_price}</td>
                    <td className="py-2 px-3 text-right font-mono">₹{t.exit_price || "-"}</td>
                    <td className="py-2 px-3 text-right">{t.quantity}</td>
                    <td className={`py-2 px-3 text-right font-mono font-bold ${
                      (t.pnl || 0) >= 0 ? "text-green-400" : "text-red-400"
                    }`}>
                      {t.pnl != null ? `₹${t.pnl.toLocaleString("en-IN")}` : "-"}
                    </td>
                    <td className="py-2 px-3 text-center text-xs text-gray-400">{t.exit_reason || "-"}</td>
                    <td className="py-2 px-3 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                        t.status === "TARGET_HIT" ? "bg-green-500/20 text-green-400" :
                        t.status === "STOPPED_OUT" ? "bg-red-500/20 text-red-400" :
                        "bg-gray-500/20 text-gray-400"
                      }`}>{t.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-gray-500">No closed trades yet.</div>
          )}
        </div>
      )}

      {/* STATS TAB */}
      {tab === "stats" && stats && (
        <div className="space-y-4">
          {/* Progress bar to live trading */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h3 className="font-semibold mb-3">Progress to Live Trading</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500 w-32">Trades (need 30)</span>
                <div className="flex-1 h-3 bg-gray-700 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${stats.closed_trades >= 30 ? "bg-green-500" : "bg-orange-500"}`}
                    style={{ width: `${Math.min(100, (stats.closed_trades / 30) * 100)}%` }} />
                </div>
                <span className="text-xs font-mono">{stats.closed_trades}/30</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500 w-32">Win Rate (need 50%)</span>
                <div className="flex-1 h-3 bg-gray-700 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${stats.win_rate >= 50 ? "bg-green-500" : "bg-red-500"}`}
                    style={{ width: `${Math.min(100, stats.win_rate)}%` }} />
                </div>
                <span className="text-xs font-mono">{stats.win_rate}%</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500 w-32">Profit Factor (1.2)</span>
                <div className="flex-1 h-3 bg-gray-700 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${stats.profit_factor >= 1.2 ? "bg-green-500" : "bg-red-500"}`}
                    style={{ width: `${Math.min(100, (stats.profit_factor / 2) * 100)}%` }} />
                </div>
                <span className="text-xs font-mono">{stats.profit_factor}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatBox label="Total P&L" value={`₹${stats.total_pnl.toLocaleString("en-IN")}`}
              color={stats.total_pnl >= 0 ? "text-green-400" : "text-red-400"} />
            <StatBox label="Win Rate" value={`${stats.win_rate}%`}
              color={stats.win_rate >= 50 ? "text-green-400" : "text-red-400"} />
            <StatBox label="Avg Win" value={`₹${stats.avg_win}`} color="text-green-400" />
            <StatBox label="Avg Loss" value={`₹${stats.avg_loss}`} color="text-red-400" />
            <StatBox label="Best Trade" value={`₹${stats.best_trade}`} color="text-green-400" />
            <StatBox label="Worst Trade" value={`₹${stats.worst_trade}`} color="text-red-400" />
            <StatBox label="Profit Factor" value={`${stats.profit_factor}`}
              color={stats.profit_factor >= 1.2 ? "text-green-400" : "text-orange-400"} />
            <StatBox label="Trades Left" value={`${stats.trades_needed || 0}`} color="text-orange-400" />
          </div>
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value, color = "text-white" }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
      <p className="text-[10px] text-gray-500 uppercase">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
    </div>
  );
}
