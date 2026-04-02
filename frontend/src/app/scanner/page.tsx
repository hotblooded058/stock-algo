"use client";

import { useEffect, useState } from "react";
import { market, trades, type WatchlistItem, type CandleResponse } from "@/lib/api";

export default function ScannerPage() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [selected, setSelected] = useState("");
  const [data, setData] = useState<CandleResponse | null>(null);
  const [interval, setInterval] = useState("1d");
  const [period, setPeriod] = useState("3mo");
  const [loading, setLoading] = useState(false);
  const [premium, setPremium] = useState(150);
  const [strength, setStrength] = useState("MODERATE");
  const [plan, setPlan] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    market.watchlist().then(setWatchlist).catch(console.error);
  }, []);

  const fetchData = async () => {
    if (!selected) return;
    setLoading(true);
    try {
      const d = await market.candles(selected, period, interval);
      setData(d);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const calcPosition = async () => {
    try {
      const result = await trades.positionSize(premium, strength);
      setPlan(result.plan as unknown as Record<string, unknown>);
    } catch (e) {
      console.error(e);
    }
  };

  const latestCandle = data?.candles?.[data.candles.length - 1];

  return (
    <div className="p-6 max-w-6xl space-y-6">
      <h1 className="text-2xl font-bold">Scanner</h1>

      {/* Controls */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm"
        >
          <option value="">Select stock...</option>
          {watchlist.map((w) => (
            <option key={w.symbol} value={w.symbol}>{w.name}</option>
          ))}
        </select>
        <select
          value={interval}
          onChange={(e) => setInterval(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
        >
          <option value="1d">Daily</option>
          <option value="1h">1 Hour</option>
          <option value="15m">15 Min</option>
          <option value="5m">5 Min</option>
        </select>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
        >
          <option value="1mo">1 Month</option>
          <option value="3mo">3 Months</option>
          <option value="6mo">6 Months</option>
          <option value="1y">1 Year</option>
        </select>
        <button
          onClick={fetchData}
          disabled={!selected || loading}
          className="px-6 py-2 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 disabled:opacity-50"
        >
          {loading ? "Loading..." : "Fetch Data"}
        </button>
      </div>

      {/* Latest Data */}
      {latestCandle && data && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
            <p className="text-xs text-gray-500">Close</p>
            <p className="text-lg font-bold font-mono">₹{latestCandle.close.toLocaleString("en-IN")}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
            <p className="text-xs text-gray-500">RSI</p>
            <p className={`text-lg font-bold ${
              (latestCandle.rsi || 50) > 70 ? "text-red-400" :
              (latestCandle.rsi || 50) < 30 ? "text-green-400" : "text-white"
            }`}>{latestCandle.rsi?.toFixed(1) || "--"}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
            <p className="text-xs text-gray-500">MACD</p>
            <p className={`text-lg font-bold ${
              (latestCandle.macd_histogram || 0) > 0 ? "text-green-400" : "text-red-400"
            }`}>{latestCandle.macd_histogram?.toFixed(2) || "--"}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
            <p className="text-xs text-gray-500">SuperTrend</p>
            <p className={`text-lg font-bold ${
              latestCandle.supertrend_dir === 1 ? "text-green-400" : "text-red-400"
            }`}>{latestCandle.supertrend_dir === 1 ? "Bullish" : "Bearish"}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
            <p className="text-xs text-gray-500">EMA 21</p>
            <p className={`text-lg font-bold ${
              latestCandle.close > (latestCandle.ema_21 || 0) ? "text-green-400" : "text-red-400"
            }`}>{latestCandle.close > (latestCandle.ema_21 || 0) ? "Above" : "Below"}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
            <p className="text-xs text-gray-500">Candles</p>
            <p className="text-lg font-bold">{data.count}</p>
          </div>
        </div>
      )}

      {/* Position Calculator */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-lg font-semibold mb-4">Position Size Calculator</h2>
        <div className="flex gap-3 flex-wrap items-end">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Premium (₹)</label>
            <input
              type="number"
              value={premium}
              onChange={(e) => setPremium(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-28"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Strength</label>
            <select
              value={strength}
              onChange={(e) => setStrength(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            >
              <option value="STRONG">Strong</option>
              <option value="MODERATE">Moderate</option>
              <option value="WEAK">Weak</option>
            </select>
          </div>
          <button
            onClick={calcPosition}
            className="px-6 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            Calculate
          </button>
        </div>

        {plan && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500">Quantity</p>
              <p className="text-lg font-bold">{String(plan.quantity)} units</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500">Total Cost</p>
              <p className="text-lg font-bold font-mono">₹{Number(plan.total_cost).toLocaleString("en-IN")}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500">Stop Loss</p>
              <p className="text-lg font-bold text-red-400 font-mono">₹{String(plan.stop_loss)}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500">Max Loss</p>
              <p className="text-lg font-bold text-red-400 font-mono">₹{Number(plan.max_loss).toLocaleString("en-IN")}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500">Target 1</p>
              <p className="text-lg font-bold text-green-400 font-mono">₹{String(plan.target_1)}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500">Target 2</p>
              <p className="text-lg font-bold text-green-400 font-mono">₹{String(plan.target_2)}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500">Risk %</p>
              <p className="text-lg font-bold">{String(plan.risk_percent)}%</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500">Signal</p>
              <p className="text-lg font-bold">{String(plan.signal_strength)}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
