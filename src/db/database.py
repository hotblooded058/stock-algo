"""
SQLite Database Layer
Handles all persistent storage for the trading platform.
"""

import sqlite3
import json
import os
from datetime import datetime, date
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'trading.db')


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA_SQL)

    # ========================================================
    # CANDLES
    # ========================================================

    def save_candles(self, symbol: str, interval: str, rows: list[dict]):
        with self._conn() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO candles
                   (symbol, interval, timestamp, open, high, low, close, volume, source)
                   VALUES (:symbol, :interval, :timestamp, :open, :high, :low, :close, :volume, :source)""",
                [{"symbol": symbol, "interval": interval, "source": "yahoo", **r} for r in rows]
            )

    def get_candles(self, symbol: str, interval: str, start: str = None, end: str = None) -> list[dict]:
        query = "SELECT * FROM candles WHERE symbol=? AND interval=?"
        params = [symbol, interval]
        if start:
            query += " AND timestamp >= ?"
            params.append(start)
        if end:
            query += " AND timestamp <= ?"
            params.append(end)
        query += " ORDER BY timestamp"
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    # ========================================================
    # OPTIONS CHAIN
    # ========================================================

    def save_options_chain(self, rows: list[dict]):
        with self._conn() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO options_chain
                   (underlying, expiry, strike, option_type, ltp, open, high, low, close,
                    volume, oi, oi_change, iv, delta, gamma, theta, vega,
                    bid, ask, bid_qty, ask_qty, fetched_at)
                   VALUES (:underlying, :expiry, :strike, :option_type, :ltp, :open, :high, :low, :close,
                           :volume, :oi, :oi_change, :iv, :delta, :gamma, :theta, :vega,
                           :bid, :ask, :bid_qty, :ask_qty, :fetched_at)""",
                rows
            )

    def get_options_chain(self, underlying: str, expiry: str = None) -> list[dict]:
        if expiry:
            query = """SELECT * FROM options_chain
                       WHERE underlying=? AND expiry=?
                       AND fetched_at = (SELECT MAX(fetched_at) FROM options_chain WHERE underlying=? AND expiry=?)
                       ORDER BY strike, option_type"""
            params = [underlying, expiry, underlying, expiry]
        else:
            query = """SELECT * FROM options_chain
                       WHERE underlying=?
                       AND fetched_at = (SELECT MAX(fetched_at) FROM options_chain WHERE underlying=?)
                       ORDER BY expiry, strike, option_type"""
            params = [underlying, underlying]
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    # ========================================================
    # SIGNALS
    # ========================================================

    def save_signal(self, signal_data: dict) -> int:
        with self._conn() as conn:
            if 'reasons' in signal_data and isinstance(signal_data['reasons'], list):
                signal_data['reasons'] = json.dumps(signal_data['reasons'])
            if 'indicators' in signal_data and isinstance(signal_data['indicators'], dict):
                signal_data['indicators'] = json.dumps(signal_data['indicators'])
            cursor = conn.execute(
                """INSERT INTO signals
                   (symbol, direction, score, strength, strategy, reasons, indicators, created_at)
                   VALUES (:symbol, :direction, :score, :strength, :strategy, :reasons, :indicators, :created_at)""",
                {**signal_data, "created_at": signal_data.get("created_at", datetime.now().isoformat())}
            )
            return cursor.lastrowid

    def get_signals(self, symbol: str = None, limit: int = 50) -> list[dict]:
        query = "SELECT * FROM signals"
        params = []
        if symbol:
            query += " WHERE symbol=?"
            params.append(symbol)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = [dict(r) for r in conn.execute(query, params).fetchall()]
            for r in rows:
                if r.get('reasons'):
                    r['reasons'] = json.loads(r['reasons'])
                if r.get('indicators'):
                    r['indicators'] = json.loads(r['indicators'])
            return rows

    def get_signal(self, signal_id: int) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM signals WHERE id=?", [signal_id]).fetchone()
            if row:
                r = dict(row)
                if r.get('reasons'):
                    r['reasons'] = json.loads(r['reasons'])
                if r.get('indicators'):
                    r['indicators'] = json.loads(r['indicators'])
                return r
            return None

    # ========================================================
    # TRADES
    # ========================================================

    def save_trade(self, trade: dict) -> int:
        with self._conn() as conn:
            if 'tags' in trade and isinstance(trade['tags'], list):
                trade['tags'] = json.dumps(trade['tags'])
            cursor = conn.execute(
                """INSERT INTO trades
                   (signal_id, symbol, instrument, direction, quantity,
                    entry_price, exit_price, stop_loss, target_1, target_2,
                    pnl, status, entry_time, exit_time, exit_reason,
                    broker_order_id, notes, tags)
                   VALUES (:signal_id, :symbol, :instrument, :direction, :quantity,
                           :entry_price, :exit_price, :stop_loss, :target_1, :target_2,
                           :pnl, :status, :entry_time, :exit_time, :exit_reason,
                           :broker_order_id, :notes, :tags)""",
                trade
            )
            return cursor.lastrowid

    def update_trade(self, trade_id: int, updates: dict):
        if 'tags' in updates and isinstance(updates['tags'], list):
            updates['tags'] = json.dumps(updates['tags'])
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [trade_id]
        with self._conn() as conn:
            conn.execute(f"UPDATE trades SET {set_clause} WHERE id=?", values)

    def get_trades(self, status: str = None, symbol: str = None, limit: int = 100) -> list[dict]:
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        if status:
            query += " AND status=?"
            params.append(status)
        if symbol:
            query += " AND symbol=?"
            params.append(symbol)
        query += " ORDER BY entry_time DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = [dict(r) for r in conn.execute(query, params).fetchall()]
            for r in rows:
                if r.get('tags'):
                    r['tags'] = json.loads(r['tags'])
            return rows

    def get_open_trades(self) -> list[dict]:
        return self.get_trades(status="OPEN")

    # ========================================================
    # DAILY P&L
    # ========================================================

    def save_daily_pnl(self, data: dict):
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO daily_pnl
                   (date, realized_pnl, unrealized_pnl, trades_taken, wins, losses,
                    capital_start, capital_end, notes)
                   VALUES (:date, :realized_pnl, :unrealized_pnl, :trades_taken, :wins, :losses,
                           :capital_start, :capital_end, :notes)""",
                data
            )

    def get_daily_pnl(self, days: int = 30) -> list[dict]:
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM daily_pnl ORDER BY date DESC LIMIT ?", [days]
            ).fetchall()]

    def get_today_pnl(self) -> dict | None:
        today = date.today().isoformat()
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM daily_pnl WHERE date=?", [today]).fetchone()
            return dict(row) if row else None

    # ========================================================
    # MARKET CONTEXT
    # ========================================================

    def save_market_context(self, data: dict):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO market_context
                   (date, time, vix, pcr, nifty_level, banknifty_level,
                    fii_net, dii_net, advance_decline_ratio, fetched_at)
                   VALUES (:date, :time, :vix, :pcr, :nifty_level, :banknifty_level,
                           :fii_net, :dii_net, :advance_decline_ratio, :fetched_at)""",
                {**data, "fetched_at": datetime.now().isoformat()}
            )

    def get_market_context(self, date_str: str = None) -> list[dict]:
        if date_str is None:
            date_str = date.today().isoformat()
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM market_context WHERE date=? ORDER BY fetched_at DESC", [date_str]
            ).fetchall()]

    # ========================================================
    # INSTRUMENTS
    # ========================================================

    def save_instruments(self, instruments: list[dict]):
        with self._conn() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO instruments
                   (symbol, exchange, token, yahoo_symbol, lot_size, tick_size,
                    instrument_type, last_updated)
                   VALUES (:symbol, :exchange, :token, :yahoo_symbol, :lot_size, :tick_size,
                           :instrument_type, :last_updated)""",
                [{**i, "last_updated": datetime.now().isoformat()} for i in instruments]
            )

    def get_instrument(self, symbol: str, exchange: str = "NSE") -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM instruments WHERE symbol=? AND exchange=?", [symbol, exchange]
            ).fetchone()
            return dict(row) if row else None

    def search_instruments(self, query: str, exchange: str = None) -> list[dict]:
        sql = "SELECT * FROM instruments WHERE symbol LIKE ?"
        params = [f"%{query}%"]
        if exchange:
            sql += " AND exchange=?"
            params.append(exchange)
        sql += " LIMIT 50"
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    # ========================================================
    # STATS
    # ========================================================

    def get_stats(self) -> dict:
        with self._conn() as conn:
            stats = {}
            for table in ['candles', 'options_chain', 'signals', 'trades', 'daily_pnl', 'market_context', 'instruments']:
                row = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
                stats[table] = row['count']
            return stats


# ============================================================
# SCHEMA
# ============================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    source TEXT DEFAULT 'yahoo',
    UNIQUE(symbol, interval, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_candles_lookup
ON candles(symbol, interval, timestamp);

CREATE TABLE IF NOT EXISTS options_chain (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    underlying TEXT NOT NULL,
    expiry TEXT NOT NULL,
    strike REAL NOT NULL,
    option_type TEXT NOT NULL,
    ltp REAL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    oi INTEGER,
    oi_change INTEGER,
    iv REAL,
    delta REAL,
    gamma REAL,
    theta REAL,
    vega REAL,
    bid REAL,
    ask REAL,
    bid_qty INTEGER,
    ask_qty INTEGER,
    fetched_at TEXT NOT NULL,
    UNIQUE(underlying, expiry, strike, option_type, fetched_at)
);

CREATE INDEX IF NOT EXISTS idx_options_lookup
ON options_chain(underlying, expiry, strike, option_type);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    score INTEGER,
    strength TEXT,
    strategy TEXT,
    reasons TEXT,
    indicators TEXT,
    created_at TEXT NOT NULL,
    acted_on INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol
ON signals(symbol, created_at);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER REFERENCES signals(id),
    symbol TEXT NOT NULL,
    instrument TEXT,
    direction TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    stop_loss REAL,
    target_1 REAL,
    target_2 REAL,
    pnl REAL,
    status TEXT DEFAULT 'OPEN',
    entry_time TEXT NOT NULL,
    exit_time TEXT,
    exit_reason TEXT,
    broker_order_id TEXT,
    notes TEXT,
    tags TEXT
);

CREATE INDEX IF NOT EXISTS idx_trades_status
ON trades(status, entry_time);

CREATE TABLE IF NOT EXISTS daily_pnl (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    realized_pnl REAL DEFAULT 0,
    unrealized_pnl REAL DEFAULT 0,
    trades_taken INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    capital_start REAL,
    capital_end REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS market_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT,
    vix REAL,
    pcr REAL,
    nifty_level REAL,
    banknifty_level REAL,
    fii_net REAL,
    dii_net REAL,
    advance_decline_ratio REAL,
    fetched_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_context_date
ON market_context(date, fetched_at);

CREATE TABLE IF NOT EXISTS instruments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    token TEXT,
    yahoo_symbol TEXT,
    lot_size INTEGER DEFAULT 1,
    tick_size REAL DEFAULT 0.05,
    instrument_type TEXT,
    last_updated TEXT,
    UNIQUE(symbol, exchange)
);
"""
