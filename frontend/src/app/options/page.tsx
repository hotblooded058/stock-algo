"use client";

import { useState } from "react";
import { options, type OptionChainEntry, type OptionsAnalytics, type StrikeRecommendation } from "@/lib/api";

const underlyings = ["NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "HDFCBANK", "INFY"];

export default function OptionsPage() {
  const [selected, setSelected] = useState("NIFTY");
  const [chain, setChain] = useState<OptionChainEntry[]>([]);
  const [analytics, setAnalytics] = useState<OptionsAnalytics | null>(null);
  const [strikeRec, setStrikeRec] = useState<StrikeRecommendation | null>(null);
  const [loading, setLoading] = useState(false);
  const [spotPrice, setSpotPrice] = useState<number>(0);
  const [tab, setTab] = useState<"chain" | "analytics" | "recommend">("chain");

  const fetchChain = async () => {
    setLoading(true);
    try {
      const data = await options.chain(selected, undefined, spotPrice || undefined);
      setChain(data.chain);
      setAnalytics(data.analytics);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecommendation = async (direction: string) => {
    if (!spotPrice) return;
    try {
      const rec = await options.recommendStrike(selected, spotPrice, direction);
      setStrikeRec(rec);
    } catch (e) {
      console.error(e);
    }
  };

  // Split chain into calls and puts by strike
  const strikes = [...new Set(chain.map((c) => c.strike))].sort((a, b) => a - b);
  const callMap = new Map(chain.filter((c) => c.option_type === "CE").map((c) => [c.strike, c]));
  const putMap = new Map(chain.filter((c) => c.option_type === "PE").map((c) => [c.strike, c]));

  return (
    <div className="p-6 max-w-7xl space-y-6">
      <h1 className="text-2xl font-bold">Options Chain</h1>

      {/* Controls */}
      <div className="flex gap-3 items-center flex-wrap">
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm"
        >
          {underlyings.map((u) => (
            <option key={u} value={u}>{u}</option>
          ))}
        </select>
        <input
          type="number"
          placeholder="Spot price"
          value={spotPrice || ""}
          onChange={(e) => setSpotPrice(Number(e.target.value))}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-32"
        />
        <button
          onClick={fetchChain}
          disabled={loading}
          className="px-6 py-2 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 disabled:opacity-50"
        >
          {loading ? "Fetching..." : "Fetch Chain"}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-800 pb-2">
        {(["chain", "analytics", "recommend"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`text-sm pb-2 capitalize ${tab === t ? "text-orange-400 border-b-2 border-orange-400" : "text-gray-500"}`}
          >
            {t === "recommend" ? "Strike Selector" : t}
          </button>
        ))}
      </div>

      {/* Analytics Summary (always visible) */}
      {analytics && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-500">PCR</p>
            <p className={`text-xl font-bold ${analytics.pcr.oi_pcr > 1 ? "text-green-400" : "text-red-400"}`}>
              {analytics.pcr.oi_pcr}
            </p>
            <p className="text-xs text-gray-500">{analytics.pcr.sentiment}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-500">Max Pain</p>
            <p className="text-xl font-bold text-orange-400">{analytics.max_pain?.strike || "--"}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-500">Support</p>
            <p className="text-xl font-bold text-green-400">{analytics.oi_levels?.support || "--"}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-500">Resistance</p>
            <p className="text-xl font-bold text-red-400">{analytics.oi_levels?.resistance || "--"}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-500">IV Skew</p>
            <p className="text-sm font-bold text-white">{analytics.iv_skew?.skew_type || "--"}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-xs text-gray-500">Bias</p>
            <p className={`text-lg font-bold ${
              analytics.summary?.bias?.includes("Bullish") ? "text-green-400" :
              analytics.summary?.bias?.includes("Bearish") ? "text-red-400" : "text-gray-400"
            }`}>{analytics.summary?.bias || "--"}</p>
          </div>
        </div>
      )}

      {/* Analytics Tab: OI Buildup Signals + Summary */}
      {tab === "analytics" && analytics && (
        <div className="grid md:grid-cols-2 gap-4">
          {/* OI Buildup */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="font-semibold mb-3">OI Buildup Signals</h3>
            {analytics.oi_buildup?.signals?.length > 0 ? (
              <div className="space-y-2">
                {analytics.oi_buildup.signals.map((sig, i) => (
                  <p key={i} className="text-sm text-gray-300">
                    <span className="text-orange-400 mr-1">*</span> {sig}
                  </p>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No significant OI changes</p>
            )}
            <div className="mt-3 pt-3 border-t border-gray-800 flex gap-6 text-xs">
              <span>Call OI Change: <span className="font-mono text-red-400">{analytics.oi_buildup?.total_call_oi_change?.toLocaleString()}</span></span>
              <span>Put OI Change: <span className="font-mono text-green-400">{analytics.oi_buildup?.total_put_oi_change?.toLocaleString()}</span></span>
            </div>
          </div>

          {/* Summary */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="font-semibold mb-3">Analysis Summary</h3>
            <div className="flex items-center gap-3 mb-3">
              <span className={`text-2xl font-bold ${
                analytics.summary?.bias?.includes("Bullish") ? "text-green-400" :
                analytics.summary?.bias?.includes("Bearish") ? "text-red-400" : "text-gray-400"
              }`}>{analytics.summary?.bias}</span>
              <span className="text-sm text-gray-500">Score: {analytics.summary?.bias_score}</span>
            </div>
            <div className="space-y-1">
              {analytics.summary?.reasons?.map((r, i) => (
                <p key={i} className="text-sm text-gray-400">
                  <span className="text-blue-400 mr-1">-</span> {r}
                </p>
              ))}
            </div>
            <div className="mt-3 pt-3 border-t border-gray-800 text-xs text-gray-500">
              <p>IV Skew: {analytics.iv_skew?.interpretation}</p>
            </div>
          </div>
        </div>
      )}

      {/* Strike Recommendation Tab */}
      {tab === "recommend" && (
        <div className="space-y-4">
          <div className="flex gap-3">
            <button
              onClick={() => fetchRecommendation("BUY_CALL")}
              disabled={!spotPrice}
              className="px-6 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              Recommend CALL Strike
            </button>
            <button
              onClick={() => fetchRecommendation("BUY_PUT")}
              disabled={!spotPrice}
              className="px-6 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:opacity-50"
            >
              Recommend PUT Strike
            </button>
            {!spotPrice && <p className="text-sm text-gray-500 self-center">Enter spot price first</p>}
          </div>

          {strikeRec?.recommended && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold">
                    {strikeRec.underlying} {strikeRec.recommended.strike} {strikeRec.recommended.option_type}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {strikeRec.direction.replace("BUY_", "")} | {strikeRec.dte_days} DTE | {strikeRec.recommended.moneyness}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-orange-400">₹{strikeRec.recommended.ltp.toFixed(2)}</p>
                  <p className="text-xs text-gray-500">Lot: ₹{strikeRec.recommended.lot_value.toLocaleString("en-IN")}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
                <div className="bg-gray-800 rounded-lg p-2 text-center">
                  <p className="text-[10px] text-gray-500">Delta</p>
                  <p className="font-bold font-mono">{strikeRec.recommended.delta.toFixed(3)}</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-2 text-center">
                  <p className="text-[10px] text-gray-500">Gamma</p>
                  <p className="font-bold font-mono">{strikeRec.recommended.gamma.toFixed(5)}</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-2 text-center">
                  <p className="text-[10px] text-gray-500">Theta/day</p>
                  <p className="font-bold font-mono text-red-400">{strikeRec.recommended.theta.toFixed(2)}</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-2 text-center">
                  <p className="text-[10px] text-gray-500">Vega</p>
                  <p className="font-bold font-mono">{strikeRec.recommended.vega.toFixed(2)}</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-2 text-center">
                  <p className="text-[10px] text-gray-500">IV</p>
                  <p className="font-bold font-mono">{strikeRec.recommended.iv.toFixed(1)}%</p>
                </div>
              </div>

              <div className="space-y-1 mb-4">
                {strikeRec.recommended.reasons.map((r, i) => (
                  <p key={i} className="text-xs text-gray-400">
                    <span className="text-green-400 mr-1">+</span> {r}
                  </p>
                ))}
              </div>

              {strikeRec.alternatives.length > 0 && (
                <div className="border-t border-gray-800 pt-3">
                  <p className="text-xs text-gray-500 mb-2">Alternatives:</p>
                  <div className="flex gap-3">
                    {strikeRec.alternatives.map((a, i) => (
                      <div key={i} className="bg-gray-800 rounded-lg px-3 py-2 text-xs">
                        <span className="font-bold">{a.strike}</span>
                        <span className="text-gray-500 ml-2">₹{a.ltp.toFixed(2)}</span>
                        <span className="text-gray-500 ml-2">delta {a.delta.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Chain Table Tab */}
      {tab === "chain" && chain.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-800">
                <th colSpan={6} className="py-2 px-2 text-center text-green-400 bg-green-500/5">CALLS</th>
                <th className="py-2 px-2 text-center text-orange-400 bg-orange-500/10">STRIKE</th>
                <th colSpan={6} className="py-2 px-2 text-center text-red-400 bg-red-500/5">PUTS</th>
              </tr>
              <tr className="text-gray-500 border-b border-gray-700">
                <th className="py-1 px-2 text-right">OI</th>
                <th className="py-1 px-2 text-right">Chg</th>
                <th className="py-1 px-2 text-right">Vol</th>
                <th className="py-1 px-2 text-right">IV</th>
                <th className="py-1 px-2 text-right">Delta</th>
                <th className="py-1 px-2 text-right">LTP</th>
                <th className="py-1 px-2 text-center font-bold">Strike</th>
                <th className="py-1 px-2 text-left">LTP</th>
                <th className="py-1 px-2 text-left">Delta</th>
                <th className="py-1 px-2 text-left">IV</th>
                <th className="py-1 px-2 text-left">Vol</th>
                <th className="py-1 px-2 text-left">Chg</th>
                <th className="py-1 px-2 text-left">OI</th>
              </tr>
            </thead>
            <tbody>
              {strikes.map((strike) => {
                const call = callMap.get(strike);
                const put = putMap.get(strike);
                const isMaxPain = analytics?.max_pain?.strike === strike;
                const isSupport = analytics?.oi_levels?.support === strike;
                const isResistance = analytics?.oi_levels?.resistance === strike;

                let rowClass = "border-b border-gray-800/50 hover:bg-gray-800/30";
                if (isMaxPain) rowClass += " bg-orange-500/10";
                if (isSupport) rowClass += " bg-green-500/5";
                if (isResistance) rowClass += " bg-red-500/5";

                return (
                  <tr key={strike} className={rowClass}>
                    <td className="py-1.5 px-2 text-right font-mono text-green-400/70">{call?.oi?.toLocaleString() || "-"}</td>
                    <td className={`py-1.5 px-2 text-right font-mono ${(call?.oi_change || 0) > 0 ? "text-green-400" : (call?.oi_change || 0) < 0 ? "text-red-400" : ""}`}>
                      {call?.oi_change?.toLocaleString() || "-"}
                    </td>
                    <td className="py-1.5 px-2 text-right font-mono">{call?.volume?.toLocaleString() || "-"}</td>
                    <td className="py-1.5 px-2 text-right font-mono">{call?.iv?.toFixed(1) || "-"}</td>
                    <td className="py-1.5 px-2 text-right font-mono text-blue-400">{call?.delta?.toFixed(2) || "-"}</td>
                    <td className="py-1.5 px-2 text-right font-mono font-medium text-green-400">{call?.ltp?.toFixed(2) || "-"}</td>
                    <td className={`py-1.5 px-2 text-center font-bold ${isMaxPain ? "text-orange-400" : isSupport ? "text-green-400" : isResistance ? "text-red-400" : "text-white"}`}>
                      {strike}
                      {isMaxPain && <span className="text-[10px] ml-1 text-orange-400">MP</span>}
                      {isSupport && <span className="text-[10px] ml-1 text-green-400">S</span>}
                      {isResistance && <span className="text-[10px] ml-1 text-red-400">R</span>}
                    </td>
                    <td className="py-1.5 px-2 text-left font-mono font-medium text-red-400">{put?.ltp?.toFixed(2) || "-"}</td>
                    <td className="py-1.5 px-2 text-left font-mono text-blue-400">{put?.delta?.toFixed(2) || "-"}</td>
                    <td className="py-1.5 px-2 text-left font-mono">{put?.iv?.toFixed(1) || "-"}</td>
                    <td className="py-1.5 px-2 text-left font-mono">{put?.volume?.toLocaleString() || "-"}</td>
                    <td className={`py-1.5 px-2 text-left font-mono ${(put?.oi_change || 0) > 0 ? "text-green-400" : (put?.oi_change || 0) < 0 ? "text-red-400" : ""}`}>
                      {put?.oi_change?.toLocaleString() || "-"}
                    </td>
                    <td className="py-1.5 px-2 text-left font-mono text-red-400/70">{put?.oi?.toLocaleString() || "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {tab === "chain" && chain.length === 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
          <p className="text-lg mb-2">No options chain data</p>
          <p className="text-sm">Connect AngelOne and fetch the chain, or click &quot;Fetch Chain&quot; to load from database.</p>
        </div>
      )}
    </div>
  );
}
