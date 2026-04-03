"use client";

import { useEffect, useState, useReducer } from "react";

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

interface DashData {
  vix: number | null;
  vixMood: string;
  vixChange: number;
  capital: number;
  dailyPnl: number;
  canTrade: boolean;
  winRate: number;
  closedTrades: number;
  totalPnl: number;
  profitFactor: number;
  db: Record<string, number>;
  loaded: boolean;
  error: string;
}

interface ScanSignal {
  symbol: string;
  name: string;
  price: number;
  change_pct: number;
  direction: string;
  score: number;
  strength: string;
  strategy: string;
  reasons: string[];
}

const defaultData: DashData = {
  vix: null, vixMood: "", vixChange: 0,
  capital: 0, dailyPnl: 0, canTrade: false,
  winRate: 0, closedTrades: 0, totalPnl: 0, profitFactor: 0,
  db: {},
  loaded: false, error: "",
};

export default function Dashboard() {
  const [data, setData] = useState<DashData>(defaultData);
  const [signals, setSignals] = useState<ScanSignal[]>([]);
  const [scanning, setScanning] = useState(false);
  const [, forceUpdate] = useReducer((x: number) => x + 1, 0);

  useEffect(() => {
    const host = window.location.hostname;
    const api = `http://${host}:8000/api`;

    async function loadData() {
      try {
        const [vixRes, sysRes, statsRes] = await Promise.all([
          fetch(`${api}/market/vix`).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`${api}/system/status`).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`${api}/trades/stats`).then(r => r.ok ? r.json() : null).catch(() => null),
        ]);

        const newData: DashData = {
          vix: vixRes?.vix ?? null,
          vixMood: vixRes?.mood ?? "",
          vixChange: vixRes?.change ?? 0,
          capital: sysRes?.risk?.capital ?? 0,
          dailyPnl: sysRes?.risk?.daily_pnl ?? 0,
          canTrade: sysRes?.risk?.can_trade ?? false,
          winRate: statsRes?.win_rate ?? 0,
          closedTrades: statsRes?.closed_trades ?? 0,
          totalPnl: statsRes?.total_pnl ?? 0,
          profitFactor: statsRes?.profit_factor ?? 0,
          db: sysRes?.db ?? {},
          loaded: true,
          error: (!vixRes && !sysRes && !statsRes) ? "Cannot connect to backend" : "",
        };

        setData(newData);
        forceUpdate();
      } catch {
        setData({ ...defaultData, loaded: true, error: "Backend connection failed" });
        forceUpdate();
      }
    }

    loadData();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      const host = window.location.hostname;
      const res = await fetch(`http://${host}:8000/api/market/scan`);
      const json = await res.json();
      setSignals(json.signals || []);
    } catch {
      // ignore
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Options trading decision support</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${data.canTrade ? "bg-green-500" : "bg-red-500"}`} />
          <span className="text-sm text-gray-400">
            {data.canTrade ? "Ready to trade" : "Trading paused"}
          </span>
        </div>
      </div>

      {data.error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-sm text-red-400">
          {data.error}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="India VIX"
          value={data.vix ? data.vix.toFixed(2) : "--"}
          subtitle={data.vixMood || undefined}
          color={data.vix && data.vix > 20 ? "text-red-400" : "text-green-400"}
        />
        <MetricCard
          title="Capital"
          value={data.capital ? `₹${data.capital.toLocaleString("en-IN")}` : "--"}
          subtitle={data.loaded ? `Daily P&L: ₹${data.dailyPnl}` : undefined}
        />
        <MetricCard
          title="Win Rate"
          value={data.loaded ? `${data.winRate}%` : "--"}
          subtitle={data.loaded ? `${data.closedTrades} trades` : undefined}
          color={data.winRate >= 50 ? "text-green-400" : "text-orange-400"}
        />
        <MetricCard
          title="Total P&L"
          value={data.loaded ? `₹${data.totalPnl.toLocaleString("en-IN")}` : "--"}
          subtitle={data.loaded ? `PF: ${data.profitFactor}` : undefined}
          color={data.totalPnl >= 0 ? "text-green-400" : "text-red-400"}
        />
      </div>

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

        {signals.length > 0 ? (
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
                {signals.map((sig, i) => (
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
            Click &quot;Scan Watchlist&quot; to find trading opportunities
          </p>
        )}
      </div>

      {Object.keys(data.db).length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-3">Database</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {Object.entries(data.db).map(([table, count]) => (
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
