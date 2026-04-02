"use client";

import { useState } from "react";
import { options, type OptionChainEntry, type OptionsAnalytics } from "@/lib/api";

const underlyings = ["NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "HDFCBANK", "INFY"];

export default function OptionsPage() {
  const [selected, setSelected] = useState("NIFTY");
  const [chain, setChain] = useState<OptionChainEntry[]>([]);
  const [analytics, setAnalytics] = useState<OptionsAnalytics | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchChain = async () => {
    setLoading(true);
    try {
      const data = await options.chain(selected);
      setChain(data.chain);
      setAnalytics(data.analytics);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // Split chain into calls and puts by strike
  const strikes = [...new Set(chain.map((c) => c.strike))].sort((a, b) => a - b);
  const callMap = new Map(chain.filter((c) => c.option_type === "CE").map((c) => [c.strike, c]));
  const putMap = new Map(chain.filter((c) => c.option_type === "PE").map((c) => [c.strike, c]));

  return (
    <div className="p-6 max-w-7xl space-y-6">
      <h1 className="text-2xl font-bold">Options Chain</h1>

      <div className="flex gap-3 items-center">
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm"
        >
          {underlyings.map((u) => (
            <option key={u} value={u}>{u}</option>
          ))}
        </select>
        <button
          onClick={fetchChain}
          disabled={loading}
          className="px-6 py-2 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 disabled:opacity-50"
        >
          {loading ? "Fetching..." : "Fetch Chain"}
        </button>
      </div>

      {/* Analytics Summary */}
      {analytics && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-500">PCR</p>
            <p className={`text-xl font-bold ${analytics.pcr > 1 ? "text-green-400" : "text-red-400"}`}>
              {analytics.pcr}
            </p>
            <p className="text-xs text-gray-500">{analytics.pcr_sentiment}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-500">Max Pain</p>
            <p className="text-xl font-bold text-white">{analytics.max_pain || "--"}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-500">Support (Put OI)</p>
            <p className="text-xl font-bold text-green-400">{analytics.support || "--"}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-500">Resistance (Call OI)</p>
            <p className="text-xl font-bold text-red-400">{analytics.resistance || "--"}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-500">Total OI</p>
            <p className="text-sm font-bold">
              <span className="text-green-400">C: {(analytics.total_call_oi / 1000).toFixed(0)}K</span>
              {" / "}
              <span className="text-red-400">P: {(analytics.total_put_oi / 1000).toFixed(0)}K</span>
            </p>
          </div>
        </div>
      )}

      {/* Chain Table */}
      {chain.length > 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-800">
                <th colSpan={5} className="py-2 px-2 text-center text-green-400 bg-green-500/5">CALLS</th>
                <th className="py-2 px-2 text-center text-orange-400 bg-orange-500/10">STRIKE</th>
                <th colSpan={5} className="py-2 px-2 text-center text-red-400 bg-red-500/5">PUTS</th>
              </tr>
              <tr className="text-gray-500 border-b border-gray-700">
                <th className="py-1 px-2 text-right">OI</th>
                <th className="py-1 px-2 text-right">Chg</th>
                <th className="py-1 px-2 text-right">Volume</th>
                <th className="py-1 px-2 text-right">IV</th>
                <th className="py-1 px-2 text-right">LTP</th>
                <th className="py-1 px-2 text-center font-bold">Strike</th>
                <th className="py-1 px-2 text-left">LTP</th>
                <th className="py-1 px-2 text-left">IV</th>
                <th className="py-1 px-2 text-left">Volume</th>
                <th className="py-1 px-2 text-left">Chg</th>
                <th className="py-1 px-2 text-left">OI</th>
              </tr>
            </thead>
            <tbody>
              {strikes.map((strike) => {
                const call = callMap.get(strike);
                const put = putMap.get(strike);
                const isMaxPain = analytics?.max_pain === strike;

                return (
                  <tr key={strike} className={`border-b border-gray-800/50 hover:bg-gray-800/30 ${isMaxPain ? "bg-orange-500/10" : ""}`}>
                    <td className="py-1.5 px-2 text-right font-mono text-green-400/70">{call?.oi?.toLocaleString() || "-"}</td>
                    <td className="py-1.5 px-2 text-right font-mono">{call?.oi_change || "-"}</td>
                    <td className="py-1.5 px-2 text-right font-mono">{call?.volume?.toLocaleString() || "-"}</td>
                    <td className="py-1.5 px-2 text-right font-mono">{call?.iv?.toFixed(1) || "-"}</td>
                    <td className="py-1.5 px-2 text-right font-mono font-medium text-green-400">{call?.ltp?.toFixed(2) || "-"}</td>
                    <td className={`py-1.5 px-2 text-center font-bold ${isMaxPain ? "text-orange-400" : "text-white"}`}>
                      {strike}
                      {isMaxPain && <span className="text-[10px] ml-1 text-orange-400">MP</span>}
                    </td>
                    <td className="py-1.5 px-2 text-left font-mono font-medium text-red-400">{put?.ltp?.toFixed(2) || "-"}</td>
                    <td className="py-1.5 px-2 text-left font-mono">{put?.iv?.toFixed(1) || "-"}</td>
                    <td className="py-1.5 px-2 text-left font-mono">{put?.volume?.toLocaleString() || "-"}</td>
                    <td className="py-1.5 px-2 text-left font-mono">{put?.oi_change || "-"}</td>
                    <td className="py-1.5 px-2 text-left font-mono text-red-400/70">{put?.oi?.toLocaleString() || "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
          <p className="text-lg mb-2">No options chain data</p>
          <p className="text-sm">Connect AngelOne and fetch the chain, or click &quot;Fetch Chain&quot; to load from database.</p>
        </div>
      )}
    </div>
  );
}
