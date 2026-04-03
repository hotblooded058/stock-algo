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
  pcr: { oi_pcr: number; volume_pcr: number; sentiment: string; total_call_oi: number; total_put_oi: number };
  max_pain: { strike: number; interpretation: string };
  oi_levels: { support: number; resistance: number; range: string; support_levels: { strike: number; oi: number }[]; resistance_levels: { strike: number; oi: number }[] };
  iv_skew: { skew_type: string; atm_iv: number; interpretation: string };
  oi_buildup: { total_call_oi_change: number; total_put_oi_change: number; signals: string[] };
  summary: { bias: string; bias_score: number; reasons: string[] };
}

export interface StrikeRecommendation {
  underlying: string;
  direction: string;
  expiry: string;
  dte_days: number;
  spot_price: number;
  recommended: {
    strike: number;
    option_type: string;
    ltp: number;
    iv: number;
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
    moneyness: string;
    score: number;
    reasons: string[];
    lot_size: number;
    lot_value: number;
  };
  alternatives: { strike: number; ltp: number; delta: number; score: number }[];
}

export interface GreeksResult {
  iv: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  theoretical_price: number;
  moneyness: string;
}

export const options = {
  chain: (underlying: string, expiry?: string, spotPrice?: number) =>
    fetcher<{ chain: OptionChainEntry[]; analytics: OptionsAnalytics }>(
      `/options/chain?underlying=${underlying}${expiry ? `&expiry=${expiry}` : ""}${spotPrice ? `&spot_price=${spotPrice}` : ""}`
    ),
  analytics: (underlying: string, spotPrice?: number) =>
    fetcher<OptionsAnalytics>(`/options/analytics?underlying=${underlying}${spotPrice ? `&spot_price=${spotPrice}` : ""}`),
  greeks: (spot: number, strike: number, expiry: string, optionType = "CE", premium?: number) =>
    fetcher<GreeksResult>(
      `/options/greeks?spot=${spot}&strike=${strike}&expiry=${expiry}&option_type=${optionType}${premium ? `&premium=${premium}` : ""}`
    ),
  recommendStrike: (underlying: string, spotPrice: number, direction: string, expiry?: string, riskProfile = "moderate") =>
    fetcher<StrikeRecommendation>(
      `/options/recommend-strike?underlying=${underlying}&spot_price=${spotPrice}&direction=${direction}&risk_profile=${riskProfile}${expiry ? `&expiry=${expiry}` : ""}`
    ),
  marketContext: () => fetcher<Record<string, unknown>>("/options/market-context"),
  fetchContext: () => poster<Record<string, unknown>>("/options/fetch-context"),
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

// ========================================================
// BACKTEST
// ========================================================

export interface BacktestMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  avg_bars_held: number;
  best_trade: number;
  worst_trade: number;
}

export interface BacktestTrade {
  direction: string;
  entry_price: number;
  exit_price: number;
  entry_date: string;
  exit_date: string;
  exit_reason: string;
  pnl: number;
  pnl_pct: number;
  bars_held: number;
  score: number;
  strategy: string;
}

export interface BacktestResult {
  symbol: string;
  period: string;
  interval: string;
  strategy: string;
  metrics: BacktestMetrics;
  trades: BacktestTrade[];
  equity_curve: number[];
  monthly_returns: Record<string, number>;
}

export const backtest = {
  run: (symbol: string, period = "1y", interval = "1d", strategy = "all", minScore = 40) =>
    fetcher<BacktestResult>(
      `/backtest/run?symbol=${symbol}&period=${period}&interval=${interval}&strategy=${strategy}&min_score=${minScore}`
    ),
};

// ========================================================
// JOURNAL
// ========================================================

export const journal = {
  report: () => fetcher<Record<string, unknown>>("/journal/report"),
};

// ========================================================
// ALERTS
// ========================================================

// ========================================================
// SCREENER
// ========================================================

export interface ScreenerSignal {
  symbol: string;
  yahoo: string;
  sector: string;
  lot_size: number;
  price: number;
  change_pct: number;
  direction: string;
  score: number;
  strength: string;
  strategy: string;
  reasons: string[];
  rsi: number | null;
  adx: number | null;
  above_vwap: boolean | null;
  supertrend: string | null;
  volume_ratio: number | null;
}

export const screener = {
  stocks: (sector?: string) =>
    fetcher<{ stocks: { symbol: string; yahoo: string; lot_size: number; sector: string }[]; count: number }>(
      `/screener/stocks${sector ? `?sector=${sector}` : ""}`
    ),
  sectors: () =>
    fetcher<{ sectors: { name: string; count: number }[] }>("/screener/sectors"),
  scan: (sector?: string, minScore = 50, limit = 50) =>
    fetcher<{ signals: ScreenerSignal[]; count: number; scanned: number; errors: number }>(
      `/screener/scan?min_score=${minScore}&limit=${limit}${sector ? `&sector=${sector}` : ""}`
    ),
  topMovers: () =>
    fetcher<{ gainers: { symbol: string; sector: string; price: number; change_pct: number }[]; losers: { symbol: string; sector: string; price: number; change_pct: number }[] }>(
      "/screener/top-movers"
    ),
};

export const alerts = {
  test: () => fetcher<{ success: boolean; channels: string[] }>("/alerts/test"),
  history: () => fetcher<{ alerts: { time: string; message: string; category: string }[] }>("/alerts/history"),
  status: () => fetcher<{ telegram_enabled: boolean; message: string }>("/alerts/status"),
};
