"use client";

import { useEffect, useState } from "react";
import { market, system, trades, type VixData, type ScanResult, type TradeStats } from "@/lib/api";

function MetricCard({ title, value, subtitle, color = "text-white" }: {
  title: string; value: string; subtitle?: string; color?: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{title}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
}

export default function Dashboard() {
  const [vix, setVix] = useState<VixData | null>(null);
  const [topSignals, setTopSignals] = useState<ScanResult[]>([]);
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [systemStatus, setSystemStatus] = useState<{
    risk: { capital: number; daily_pnl: number; can_trade: boolean };
    db: Record<string, number>;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [v, sys, st] = await Promise.all([
          market.vix().catch(() => null),
          system.status().catch(() => null),
          trades.stats().catch(() => null),
        ]);
        setVix(v);
        setSystemStatus(sys);
        setStats(st);
      } catch (e) {
        console.error("Load error:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      const data = await market.scan();
      setTopSignals(data.signals);
    } catch {
      console.error("Scan failed");
    } finally {
      setScanning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Options trading decision support</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${systemStatus?.risk?.can_trade ? "bg-green-500" : "bg-red-500"}`} />
          <span className="text-sm text-gray-400">
            {systemStatus?.risk?.can_trade ? "Ready to trade" : "Trading paused"}
          </span>
        </div>
      </div>

      {/* Top Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="India VIX"
          value={vix ? vix.vix.toFixed(2) : "--"}
          subtitle={vix?.mood}
          color={vix && vix.vix > 20 ? "text-red-400" : "text-green-400"}
        />
        <MetricCard
          title="Capital"
          value={systemStatus ? `₹${systemStatus.risk.capital.toLocaleString("en-IN")}` : "--"}
          subtitle={systemStatus ? `Daily P&L: ₹${systemStatus.risk.daily_pnl}` : undefined}
        />
        <MetricCard
          title="Win Rate"
          value={stats ? `${stats.win_rate}%` : "--"}
          subtitle={stats ? `${stats.closed_trades} trades` : undefined}
          color={stats && stats.win_rate >= 50 ? "text-green-400" : "text-orange-400"}
        />
        <MetricCard
          title="Total P&L"
          value={stats ? `₹${stats.total_pnl.toLocaleString("en-IN")}` : "--"}
          subtitle={stats ? `PF: ${stats.profit_factor}` : undefined}
          color={stats && stats.total_pnl >= 0 ? "text-green-400" : "text-red-400"}
        />
      </div>

      {/* Quick Scan */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Quick Scan</h2>
          <button
            onClick={handleScan}
            disabled={scanning}
            className="px-4 py-1.5 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 transition disabled:opacity-50"
          >
            {scanning ? "Scanning..." : "Scan Watchlist"}
          </button>
        </div>

        {topSignals.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="text-left py-2 px-3">Stock</th>
                  <th className="text-left py-2 px-3">Price</th>
                  <th className="text-left py-2 px-3">Signal</th>
                  <th className="text-left py-2 px-3">Score</th>
                  <th className="text-left py-2 px-3">Strength</th>
                  <th className="text-left py-2 px-3">Strategy</th>
                </tr>
              </thead>
              <tbody>
                {topSignals.map((sig, i) => (
                  <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-2 px-3 font-medium">{sig.name}</td>
                    <td className="py-2 px-3">
                      <span className="font-mono">₹{sig.price.toLocaleString("en-IN")}</span>
                      <span className={`ml-2 text-xs ${sig.change_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                        {sig.change_pct >= 0 ? "+" : ""}{sig.change_pct.toFixed(2)}%
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        sig.direction.includes("CALL") ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                      }`}>
                        {sig.direction.replace("BUY_", "")}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              sig.score >= 80 ? "bg-green-500" : sig.score >= 60 ? "bg-orange-500" : "bg-gray-500"
                            }`}
                            style={{ width: `${sig.score}%` }}
                          />
                        </div>
                        <span>{sig.score}</span>
                      </div>
                    </td>
                    <td className="py-2 px-3">
                      <span className={`text-xs font-medium ${
                        sig.strength === "STRONG" ? "text-green-400" : sig.strength === "MODERATE" ? "text-orange-400" : "text-gray-400"
                      }`}>
                        {sig.strength}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-gray-400 capitalize">{sig.strategy}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">
            Click &quot;Scan Watchlist&quot; to find trading opportunities across your watchlist
          </p>
        )}
      </div>

      {/* System Status */}
      {systemStatus && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-3">Database</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {Object.entries(systemStatus.db).map(([table, count]) => (
              <div key={table} className="flex justify-between bg-gray-800/50 rounded-lg px-3 py-2">
                <span className="text-gray-400 capitalize">{table.replace("_", " ")}</span>
                <span className="font-mono text-gray-200">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
