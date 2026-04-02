const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function poster<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ========================================================
// MARKET
// ========================================================

export interface WatchlistItem {
  symbol: string;
  name: string;
}

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema_9?: number;
  ema_21?: number;
  ema_50?: number;
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  macd_histogram?: number;
  supertrend?: number;
  supertrend_dir?: number;
  bb_upper?: number;
  bb_lower?: number;
  bb_middle?: number;
}

export interface CandleResponse {
  symbol: string;
  name: string;
  interval: string;
  count: number;
  candles: Candle[];
}

export interface VixData {
  vix: number;
  change: number;
  mood: string;
  timestamp: string;
}

export interface ScanResult {
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

export const market = {
  watchlist: () => fetcher<WatchlistItem[]>("/market/watchlist"),
  candles: (symbol: string, period = "3mo", interval = "1d") =>
    fetcher<CandleResponse>(`/market/candles?symbol=${symbol}&period=${period}&interval=${interval}`),
  indicators: (symbol: string) =>
    fetcher<{ symbol: string; indicators: Record<string, unknown> }>(`/market/indicators?symbol=${symbol}`),
  vix: () => fetcher<VixData>("/market/vix"),
  scan: () => fetcher<{ signals: ScanResult[]; count: number }>("/market/scan"),
};

// ========================================================
// SIGNALS
// ========================================================

export interface Signal {
  id?: number;
  symbol: string;
  name?: string;
  direction: string;
  score: number;
  strength: string;
  strategy: string;
  reasons: string[];
  created_at?: string;
}

export const signals = {
  generate: (symbol: string) =>
    fetcher<{ signals: Signal[] }>(`/signals/generate?symbol=${symbol}`),
  history: (symbol?: string, limit = 50) =>
    fetcher<{ signals: Signal[] }>(`/signals/history?limit=${limit}${symbol ? `&symbol=${symbol}` : ""}`),
  get: (id: number) => fetcher<Signal>(`/signals/${id}`),
};

// ========================================================
// TRADES
// ========================================================

export interface Trade {
  id: number;
  signal_id?: number;
  symbol: string;
  instrument?: string;
  direction: string;
  quantity: number;
  entry_price: number;
  exit_price?: number;
  stop_loss?: number;
  target_1?: number;
  target_2?: number;
  pnl?: number;
  status: string;
  entry_time: string;
  exit_time?: string;
  exit_reason?: string;
  notes?: string;
  tags?: string[];
}

export interface TradeStats {
  total_trades: number;
  open_trades: number;
  closed_trades: number;
  win_rate: number;
  total_pnl: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  best_trade?: number;
  worst_trade?: number;
}

export interface PositionPlan {
  quantity: number;
  entry_price: number;
  stop_loss: number;
  target_1: number;
  target_2: number;
  total_cost: number;
  max_loss: number;
  risk_percent: number;
  signal_strength: string;
}

export const trades = {
  list: (status?: string) =>
    fetcher<{ trades: Trade[] }>(`/trades/?${status ? `status=${status}` : ""}`),
  open: () => fetcher<{ trades: Trade[] }>("/trades/open"),
  create: (trade: Omit<Trade, "id" | "status" | "pnl" | "entry_time">) =>
    poster<{ id: number }>("/trades/", trade),
  close: (id: number, exitPrice: number, reason = "manual") =>
    poster<{ pnl: number; status: string }>(`/trades/${id}/close`, {
      exit_price: exitPrice,
      exit_reason: reason,
    }),
  positionSize: (premium: number, strength = "MODERATE") =>
    fetcher<{ can_trade: boolean; plan: PositionPlan }>(
      `/trades/position-size?premium=${premium}&strength=${strength}`
    ),
  stats: () => fetcher<TradeStats>("/trades/stats"),
  dailyPnl: (days = 30) =>
    fetcher<{ daily_pnl: { date: string; realized_pnl: number }[] }>(`/trades/daily-pnl?days=${days}`),
};

// ========================================================
// OPTIONS
// ========================================================

export interface OptionChainEntry {
  underlying: string;
  expiry: string;
  strike: number;
  option_type: string;
  ltp: number;
  volume: number;
  oi: number;
  oi_change: number;
  iv?: number;
  delta?: number;
  theta?: number;
  bid: number;
  ask: number;
}

export interface OptionsAnalytics {
  pcr: number;
  pcr_sentiment: string;
  max_pain: number;
  total_call_oi: number;
  total_put_oi: number;
  support?: number;
  resistance?: number;
}

export const options = {
  chain: (underlying: string, expiry?: string) =>
    fetcher<{ chain: OptionChainEntry[]; analytics: OptionsAnalytics }>(
      `/options/chain?underlying=${underlying}${expiry ? `&expiry=${expiry}` : ""}`
    ),
  analytics: (underlying: string) =>
    fetcher<OptionsAnalytics>(`/options/analytics?underlying=${underlying}`),
};

// ========================================================
// SYSTEM
// ========================================================

export const system = {
  status: () => fetcher<{
    db: Record<string, number>;
    risk: { can_trade: boolean; message: string; capital: number; daily_pnl: number };
    broker: { connected: boolean; name: string };
  }>("/system/status"),
  health: () => fetcher<{ status: string }>("/health"),
};
