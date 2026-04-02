"use client";

import { useEffect, useState } from "react";
import { trades, journal, type Trade, type TradeStats } from "@/lib/api";

export default function TradesPage() {
  const [allTrades, setAllTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [journalData, setJournalData] = useState<Record<string, unknown> | null>(null);
  const [filter, setFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"journal" | "stats" | "analytics">("journal");

  useEffect(() => {
    async function load() {
      try {
        const [t, s, j] = await Promise.all([
          trades.list(),
          trades.stats(),
          journal.report().catch(() => null),
        ]);
        setAllTrades(t.trades);
        setStats(s);
        setJournalData(j);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = filter
    ? allTrades.filter((t) => t.status === filter)
    : allTrades;

  return (
    <div className="p-6 max-w-6xl space-y-6">
      <h1 className="text-2xl font-bold">Trade Journal</h1>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-800 pb-2">
        <button
          onClick={() => setTab("journal")}
          className={`text-sm pb-2 ${tab === "journal" ? "text-orange-400 border-b-2 border-orange-400" : "text-gray-500"}`}
        >
          Journal
        </button>
        <button
          onClick={() => setTab("stats")}
          className={`text-sm pb-2 ${tab === "stats" ? "text-orange-400 border-b-2 border-orange-400" : "text-gray-500"}`}
        >
          Statistics
        </button>
        <button
          onClick={() => setTab("analytics")}
          className={`text-sm pb-2 ${tab === "analytics" ? "text-orange-400 border-b-2 border-orange-400" : "text-gray-500"}`}
        >
          Analytics
        </button>
      </div>

      {tab === "stats" && stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Trades" value={stats.total_trades.toString()} />
          <StatCard label="Open" value={stats.open_trades.toString()} color="text-blue-400" />
          <StatCard
            label="Win Rate"
            value={`${stats.win_rate}%`}
            color={stats.win_rate >= 50 ? "text-green-400" : "text-red-400"}
          />
          <StatCard
            label="Total P&L"
            value={`₹${stats.total_pnl.toLocaleString("en-IN")}`}
            color={stats.total_pnl >= 0 ? "text-green-400" : "text-red-400"}
          />
          <StatCard label="Avg Win" value={`₹${stats.avg_win}`} color="text-green-400" />
          <StatCard label="Avg Loss" value={`₹${stats.avg_loss}`} color="text-red-400" />
          <StatCard label="Profit Factor" value={stats.profit_factor.toString()} />
          <StatCard
            label="Best / Worst"
            value={`₹${stats.best_trade} / ₹${stats.worst_trade}`}
          />
        </div>
      )}

      {tab === "journal" && (
        <>
          {/* Filters */}
          <div className="flex gap-2">
            {["", "OPEN", "CLOSED", "STOPPED_OUT", "TARGET_HIT"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 text-xs rounded-lg ${
                  filter === f ? "bg-orange-500 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {f || "All"}
              </button>
            ))}
          </div>

          {loading ? (
            <p className="text-gray-500 text-sm">Loading trades...</p>
          ) : filtered.length > 0 ? (
            <div className="space-y-2">
              {filtered.map((trade) => (
                <TradeRow key={trade.id} trade={trade} />
              ))}
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
              <p className="text-lg mb-2">No trades recorded yet</p>
              <p className="text-sm">Use the API to record trades or connect AngelOne for automatic tracking.</p>
            </div>
          )}
        </>
      )}

      {tab === "analytics" && journalData && (
        <AnalyticsView data={journalData} />
      )}

      {tab === "analytics" && !journalData && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
          <p>No trade data for analytics. Record some trades first.</p>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color = "text-white" }: {
  label: string; value: string; color?: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <p className="text-xs text-gray-500 uppercase">{label}</p>
      <p className={`text-xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  );
}

interface Streaks { max_win_streak: number; max_loss_streak: number; current_streak: string; current_streak_count: number }
interface DayPerf { day: string; trades: number; win_rate: number; total_pnl: number }

function AnalyticsView({ data }: { data: Record<string, unknown> }) {
  const streaks = data.streaks as Streaks | undefined;
  const suggestions = data.improvement_areas as string[] | undefined;
  const byDay = data.by_day_of_week as DayPerf[] | undefined;

  return (
    <div className="space-y-4">
      {streaks && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="font-semibold mb-3">Streaks</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">Best Win Streak</p>
              <p className="text-xl font-bold text-green-400">{streaks.max_win_streak}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">Worst Loss Streak</p>
              <p className="text-xl font-bold text-red-400">{streaks.max_loss_streak}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">Current</p>
              <p className={`text-xl font-bold ${streaks.current_streak === "win" ? "text-green-400" : "text-red-400"}`}>
                {streaks.current_streak_count} {streaks.current_streak}
              </p>
            </div>
          </div>
        </div>
      )}

      {suggestions && suggestions.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="font-semibold mb-3">Improvement Areas</h3>
          <div className="space-y-2">
            {suggestions.map((s, i) => (
              <p key={i} className="text-sm text-gray-300">
                <span className="text-orange-400 mr-2">*</span>{s}
              </p>
            ))}
          </div>
        </div>
      )}

      {byDay && byDay.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="font-semibold mb-3">Performance by Day</h3>
          <div className="grid grid-cols-5 gap-2">
            {byDay.map((d) => (
              <div key={d.day} className={`rounded-lg p-2 text-center text-xs ${d.total_pnl >= 0 ? "bg-green-500/10" : "bg-red-500/10"}`}>
                <p className="text-gray-500">{d.day.slice(0, 3)}</p>
                <p className={`font-bold ${d.total_pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {d.total_pnl >= 0 ? "+" : ""}₹{d.total_pnl}
                </p>
                <p className="text-gray-500">{d.win_rate}% WR</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TradeRow({ trade }: { trade: Trade }) {
  const isCall = trade.direction.includes("CALL");
  const statusColors: Record<string, string> = {
    OPEN: "bg-blue-500/20 text-blue-400",
    CLOSED: "bg-gray-500/20 text-gray-400",
    STOPPED_OUT: "bg-red-500/20 text-red-400",
    TARGET_HIT: "bg-green-500/20 text-green-400",
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
          isCall ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
        }`}>
          {trade.direction.replace("BUY_", "")}
        </span>
        <div>
          <p className="font-medium">{trade.symbol}</p>
          <p className="text-xs text-gray-500">
            {trade.instrument || ""} x{trade.quantity} @ ₹{trade.entry_price}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-6 text-sm">
        {trade.stop_loss && (
          <div className="text-center">
            <p className="text-[10px] text-gray-500">SL</p>
            <p className="text-red-400 font-mono">₹{trade.stop_loss}</p>
          </div>
        )}
        {trade.target_1 && (
          <div className="text-center">
            <p className="text-[10px] text-gray-500">T1</p>
            <p className="text-green-400 font-mono">₹{trade.target_1}</p>
          </div>
        )}
        {trade.pnl !== null && trade.pnl !== undefined && (
          <div className="text-center">
            <p className="text-[10px] text-gray-500">P&L</p>
            <p className={`font-bold font-mono ${trade.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
              {trade.pnl >= 0 ? "+" : ""}₹{trade.pnl}
            </p>
          </div>
        )}
        <span className={`px-2 py-0.5 rounded text-xs ${statusColors[trade.status] || "bg-gray-700 text-gray-400"}`}>
          {trade.status}
        </span>
      </div>
    </div>
  );
}
