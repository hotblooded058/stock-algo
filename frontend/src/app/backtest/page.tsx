"use client";

import { useEffect, useState } from "react";
import { backtest, market, type BacktestResult, type WatchlistItem } from "@/lib/api";

export default function BacktestPage() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [symbol, setSymbol] = useState("^NSEI");
  const [period, setPeriod] = useState("1y");
  const [interval, setInterval] = useState("1d");
  const [strategy, setStrategy] = useState("all");
  const [minScore, setMinScore] = useState(40);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    market.watchlist().then(setWatchlist).catch(console.error);
  }, []);

  const runBacktest = async () => {
    setLoading(true);
    try {
      const data = await backtest.run(symbol, period, interval, strategy, minScore);
      setResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const m = result?.metrics;

  return (
    <div className="p-6 max-w-6xl space-y-6">
      <h1 className="text-2xl font-bold">Backtesting</h1>
      <p className="text-sm text-gray-500">Test your strategies on historical data before risking real money</p>

      {/* Controls */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex gap-3 flex-wrap items-end">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Symbol</label>
            <select value={symbol} onChange={(e) => setSymbol(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
              {watchlist.map((w) => (
                <option key={w.symbol} value={w.symbol}>{w.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Period</label>
            <select value={period} onChange={(e) => setPeriod(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
              <option value="3mo">3 Months</option>
              <option value="6mo">6 Months</option>
              <option value="1y">1 Year</option>
              <option value="2y">2 Years</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Interval</label>
            <select value={interval} onChange={(e) => setInterval(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
              <option value="1d">Daily</option>
              <option value="1h">Hourly</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Strategy</label>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
              <option value="all">All</option>
              <option value="trend">Trend Only</option>
              <option value="breakout">Breakout Only</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Min Score</label>
            <input type="number" value={minScore} onChange={(e) => setMinScore(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-20" />
          </div>
          <button onClick={runBacktest} disabled={loading}
            className="px-6 py-2 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 disabled:opacity-50">
            {loading ? "Running..." : "Run Backtest"}
          </button>
        </div>
      </div>

      {/* Results */}
      {m && (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <MetricBox label="Total P&L" value={`₹${m.total_pnl.toLocaleString("en-IN")}`}
              sub={`${m.total_pnl_pct >= 0 ? "+" : ""}${m.total_pnl_pct}%`}
              color={m.total_pnl >= 0 ? "text-green-400" : "text-red-400"} />
            <MetricBox label="Win Rate" value={`${m.win_rate}%`}
              sub={`${m.winning_trades}W / ${m.losing_trades}L`}
              color={m.win_rate >= 50 ? "text-green-400" : "text-red-400"} />
            <MetricBox label="Profit Factor" value={m.profit_factor.toString()}
              sub={`Avg W: ₹${m.avg_win} / L: ₹${m.avg_loss}`}
              color={m.profit_factor >= 1.5 ? "text-green-400" : m.profit_factor >= 1 ? "text-orange-400" : "text-red-400"} />
            <MetricBox label="Max Drawdown" value={`₹${m.max_drawdown.toLocaleString("en-IN")}`}
              sub={`${m.max_drawdown_pct}%`} color="text-red-400" />
            <MetricBox label="Sharpe Ratio" value={m.sharpe_ratio.toString()}
              sub={`${m.total_trades} trades, avg ${m.avg_bars_held} bars`}
              color={m.sharpe_ratio >= 1 ? "text-green-400" : "text-orange-400"} />
          </div>

          {/* Equity Curve */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="font-semibold mb-3">Equity Curve</h3>
            <div className="h-48 flex items-end gap-px">
              {result.equity_curve.length > 0 && (() => {
                const curve = result.equity_curve;
                const min = Math.min(...curve);
                const max = Math.max(...curve);
                const range = max - min || 1;
                const step = Math.max(1, Math.floor(curve.length / 200));
                const sampled = curve.filter((_, i) => i % step === 0);

                return sampled.map((val, i) => {
                  const height = ((val - min) / range) * 100;
                  const isGain = val >= curve[0];
                  return (
                    <div key={i} className="flex-1 min-w-[1px]" style={{ height: "100%" }}>
                      <div className="w-full flex items-end h-full">
                        <div
                          className={`w-full rounded-sm ${isGain ? "bg-green-500/60" : "bg-red-500/60"}`}
                          style={{ height: `${Math.max(height, 1)}%` }}
                        />
                      </div>
                    </div>
                  );
                });
              })()}
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Start: ₹{result.equity_curve[0]?.toLocaleString("en-IN")}</span>
              <span>End: ₹{result.equity_curve[result.equity_curve.length - 1]?.toLocaleString("en-IN")}</span>
            </div>
          </div>

          {/* Monthly Returns */}
          {Object.keys(result.monthly_returns).length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <h3 className="font-semibold mb-3">Monthly Returns</h3>
              <div className="grid grid-cols-4 md:grid-cols-6 gap-2">
                {Object.entries(result.monthly_returns).map(([month, pnl]) => (
                  <div key={month} className={`rounded-lg p-2 text-center text-xs ${
                    pnl >= 0 ? "bg-green-500/10" : "bg-red-500/10"
                  }`}>
                    <p className="text-gray-500">{month}</p>
                    <p className={`font-bold font-mono ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {pnl >= 0 ? "+" : ""}₹{pnl.toLocaleString("en-IN")}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Trade List */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="font-semibold mb-3">Trades ({result.trades.length})</h3>
            <div className="overflow-x-auto max-h-80 overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-gray-900">
                  <tr className="text-gray-500 border-b border-gray-700">
                    <th className="py-1 px-2 text-left">Date</th>
                    <th className="py-1 px-2 text-left">Direction</th>
                    <th className="py-1 px-2 text-right">Entry</th>
                    <th className="py-1 px-2 text-right">Exit</th>
                    <th className="py-1 px-2 text-right">P&L</th>
                    <th className="py-1 px-2 text-left">Exit Reason</th>
                    <th className="py-1 px-2 text-right">Score</th>
                    <th className="py-1 px-2 text-left">Strategy</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((t, i) => (
                    <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                      <td className="py-1 px-2 text-gray-400">{t.entry_date.split("T")[0]}</td>
                      <td className="py-1 px-2">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                          t.direction.includes("CALL") ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                        }`}>{t.direction.replace("BUY_", "")}</span>
                      </td>
                      <td className="py-1 px-2 text-right font-mono">₹{t.entry_price.toLocaleString("en-IN")}</td>
                      <td className="py-1 px-2 text-right font-mono">₹{t.exit_price.toLocaleString("en-IN")}</td>
                      <td className={`py-1 px-2 text-right font-mono font-medium ${t.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                        {t.pnl >= 0 ? "+" : ""}₹{t.pnl.toLocaleString("en-IN")}
                      </td>
                      <td className="py-1 px-2 text-gray-400">{t.exit_reason}</td>
                      <td className="py-1 px-2 text-right">{t.score}</td>
                      <td className="py-1 px-2 text-gray-400 capitalize">{t.strategy}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {!result && !loading && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
          <p className="text-lg mb-2">Run a backtest to validate your strategy</p>
          <p className="text-sm">Select a symbol, period, and strategy above, then click &quot;Run Backtest&quot;</p>
        </div>
      )}
    </div>
  );
}

function MetricBox({ label, value, sub, color = "text-white" }: {
  label: string; value: string; sub?: string; color?: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
      <p className="text-[10px] text-gray-500 uppercase">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-[10px] text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}
