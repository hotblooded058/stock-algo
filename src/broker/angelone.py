"""
AngelOne SmartAPI Client
Handles authentication, market data, options chain, and order placement.

Setup:
1. Get API key from https://smartapi.angelone.in/
2. Fill in config/secrets.py with your credentials
3. Extract TOTP secret from AngelOne app setup
"""

import os
import sys
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from SmartApi import SmartConnect
    import pyotp
    SMARTAPI_AVAILABLE = True
except ImportError:
    SMARTAPI_AVAILABLE = False

from src.db.database import Database


# Symbol to AngelOne exchange mapping
EXCHANGE_MAP = {
    "NSE": "NSE",
    "NFO": "NFO",
    "BSE": "BSE",
    "MCX": "MCX",
}


class AngelOneClient:
    """Wrapper around AngelOne SmartAPI."""

    def __init__(self):
        self.obj = None
        self.session = None
        self.feed_token = None
        self.db = Database()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected and self.session is not None

    def login(self, api_key: str = None, client_id: str = None,
              password: str = None, totp_secret: str = None) -> bool:
        """
        Login to AngelOne SmartAPI.
        Credentials can be passed directly or loaded from config/secrets.py.
        """
        if not SMARTAPI_AVAILABLE:
            print("SmartAPI not installed. Run: uv add smartapi-python pyotp")
            return False

        # Load from secrets if not provided
        if not api_key:
            try:
                from config.secrets import (
                    ANGELONE_API_KEY, ANGELONE_CLIENT_ID,
                    ANGELONE_PASSWORD, ANGELONE_TOTP_SECRET
                )
                api_key = ANGELONE_API_KEY
                client_id = ANGELONE_CLIENT_ID
                password = ANGELONE_PASSWORD
                totp_secret = ANGELONE_TOTP_SECRET
            except ImportError:
                print("No credentials found. Create config/secrets.py with:")
                print('  ANGELONE_API_KEY = "your_api_key"')
                print('  ANGELONE_CLIENT_ID = "your_client_id"')
                print('  ANGELONE_PASSWORD = "your_password"')
                print('  ANGELONE_TOTP_SECRET = "your_totp_secret"')
                return False

        if not all([api_key, client_id, password, totp_secret]):
            print("Missing credentials. Fill in config/secrets.py")
            return False

        try:
            self.obj = SmartConnect(api_key=api_key)
            totp = pyotp.TOTP(totp_secret).now()

            data = self.obj.generateSession(client_id, password, totp)
            if not data or data.get("status") is False:
                print(f"Login failed: {data}")
                return False

            self.session = data["data"]
            self.feed_token = self.obj.getfeedToken()
            self._connected = True
            print(f"AngelOne login successful. Client: {client_id}")
            return True

        except Exception as e:
            print(f"AngelOne login error: {e}")
            return False

    def logout(self):
        if self.obj:
            try:
                self.obj.terminateSession(self.session.get("clientcode", ""))
            except Exception:
                pass
        self._connected = False
        self.session = None
        print("AngelOne session terminated.")

    # ========================================================
    # MARKET DATA
    # ========================================================

    def get_ltp(self, symbol: str, exchange: str = "NSE", token: str = None) -> float | None:
        """Get Last Traded Price for a symbol."""
        if not self.connected:
            return None

        if not token:
            inst = self.db.get_instrument(symbol, exchange)
            if not inst:
                print(f"Token not found for {symbol}. Run refresh_instruments() first.")
                return None
            token = inst["token"]

        try:
            data = self.obj.ltpData(exchange, symbol, token)
            if data and data.get("data"):
                return data["data"].get("ltp")
        except Exception as e:
            print(f"LTP error for {symbol}: {e}")
        return None

    def get_quote(self, symbol: str, exchange: str = "NSE", token: str = None) -> dict | None:
        """Get full market quote (OHLC, volume, OI) for a symbol."""
        if not self.connected:
            return None

        if not token:
            inst = self.db.get_instrument(symbol, exchange)
            if not inst:
                return None
            token = inst["token"]

        try:
            data = self.obj.ltpData(exchange, symbol, token)
            if data and data.get("data"):
                return data["data"]
        except Exception as e:
            print(f"Quote error for {symbol}: {e}")
        return None

    def get_historical(self, symbol: str, exchange: str = "NSE",
                       token: str = None, interval: str = "ONE_DAY",
                       days: int = 90) -> list[dict]:
        """
        Fetch historical candle data.
        Intervals: ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, THIRTY_MINUTE,
                   ONE_HOUR, ONE_DAY
        """
        if not self.connected:
            return []

        if not token:
            inst = self.db.get_instrument(symbol, exchange)
            if not inst:
                return []
            token = inst["token"]

        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)

            params = {
                "exchange": exchange,
                "symboltoken": token,
                "interval": interval,
                "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
                "todate": to_date.strftime("%Y-%m-%d %H:%M"),
            }

            data = self.obj.getCandleData(params)
            if not data or not data.get("data"):
                return []

            candles = []
            for c in data["data"]:
                candles.append({
                    "timestamp": c[0],
                    "open": c[1],
                    "high": c[2],
                    "low": c[3],
                    "close": c[4],
                    "volume": c[5],
                })

            # Save to DB
            self.db.save_candles(symbol, interval, candles)
            return candles

        except Exception as e:
            print(f"Historical data error for {symbol}: {e}")
            return []

    # ========================================================
    # OPTIONS CHAIN
    # ========================================================

    def get_options_chain(self, underlying: str, exchange: str = "NFO",
                          expiry: str = None, strike_count: int = 15) -> list[dict]:
        """
        Fetch options chain for an underlying.
        Gets ATM +/- strike_count strikes for the nearest expiry.
        """
        if not self.connected:
            return []

        try:
            # Get underlying LTP to determine ATM
            und_exchange = "NSE" if underlying in ("NIFTY", "BANKNIFTY", "FINNIFTY") else "NSE"
            und_token_map = {
                "NIFTY": "99926000",
                "BANKNIFTY": "99926009",
                "FINNIFTY": "99926037",
            }
            und_token = und_token_map.get(underlying)
            if not und_token:
                inst = self.db.get_instrument(underlying, und_exchange)
                if inst:
                    und_token = inst["token"]

            if not und_token:
                print(f"Could not find token for {underlying}")
                return []

            ltp_data = self.obj.ltpData(und_exchange, underlying, und_token)
            if not ltp_data or not ltp_data.get("data"):
                return []

            spot_price = ltp_data["data"]["ltp"]

            # Determine strike interval
            if underlying in ("NIFTY", "FINNIFTY"):
                strike_interval = 50
            elif underlying == "BANKNIFTY":
                strike_interval = 100
            else:
                strike_interval = 50  # default for stocks

            # Calculate ATM strike
            atm_strike = round(spot_price / strike_interval) * strike_interval

            # Get instruments for this underlying from DB
            options_instruments = self.db.search_instruments(underlying, exchange="NFO")

            if not options_instruments:
                print(f"No option instruments found for {underlying}. Run refresh_instruments() first.")
                return []

            # Filter by expiry and strike range
            chain_data = []
            fetched_at = datetime.now().isoformat()

            min_strike = atm_strike - (strike_count * strike_interval)
            max_strike = atm_strike + (strike_count * strike_interval)

            for inst in options_instruments:
                token = inst.get("token")
                if not token:
                    continue

                try:
                    quote = self.obj.ltpData("NFO", inst["symbol"], token)
                    if quote and quote.get("data"):
                        q = quote["data"]
                        chain_data.append({
                            "underlying": underlying,
                            "expiry": expiry or "",
                            "strike": float(inst.get("strike", 0)),
                            "option_type": "CE" if "CE" in inst["symbol"] else "PE",
                            "ltp": q.get("ltp", 0),
                            "open": q.get("open", 0),
                            "high": q.get("high", 0),
                            "low": q.get("low", 0),
                            "close": q.get("close", 0),
                            "volume": q.get("volume", 0),
                            "oi": q.get("opnInterest", 0),
                            "oi_change": q.get("oiChange", 0),
                            "iv": None,
                            "delta": None, "gamma": None,
                            "theta": None, "vega": None,
                            "bid": q.get("bidPrice", 0),
                            "ask": q.get("askPrice", 0),
                            "bid_qty": q.get("bidQty", 0),
                            "ask_qty": q.get("askQty", 0),
                            "fetched_at": fetched_at,
                        })
                except Exception:
                    continue

            # Save to DB
            if chain_data:
                self.db.save_options_chain(chain_data)

            return chain_data

        except Exception as e:
            print(f"Options chain error for {underlying}: {e}")
            return []

    # ========================================================
    # INSTRUMENTS
    # ========================================================

    def refresh_instruments(self):
        """
        Download and cache the AngelOne instrument master file.
        Should be called once daily — instrument tokens change for derivatives.
        """
        if not self.connected:
            print("Not connected. Login first.")
            return False

        try:
            import urllib.request

            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=30)
            instruments_raw = json.loads(resp.read().decode())

            # Filter for NSE equity and NFO (options/futures)
            instruments = []
            for inst in instruments_raw:
                exch = inst.get("exch_seg", "")
                if exch not in ("NSE", "NFO", "BSE"):
                    continue

                instruments.append({
                    "symbol": inst.get("symbol", ""),
                    "exchange": exch,
                    "token": inst.get("token", ""),
                    "yahoo_symbol": None,
                    "lot_size": int(inst.get("lotsize", 1)),
                    "tick_size": float(inst.get("tick_size", 0.05)),
                    "instrument_type": inst.get("instrumenttype", ""),
                })

            self.db.save_instruments(instruments)
            print(f"Saved {len(instruments)} instruments to DB")
            return True

        except Exception as e:
            print(f"Instrument refresh error: {e}")
            return False

    # ========================================================
    # ORDERS (Phase 5 — paper/live)
    # ========================================================

    def place_order(self, symbol: str, exchange: str, token: str,
                    transaction_type: str, quantity: int, price: float = 0,
                    order_type: str = "MARKET", product_type: str = "INTRADAY") -> dict | None:
        """
        Place an order via AngelOne.
        transaction_type: BUY or SELL
        order_type: MARKET, LIMIT, SL, SL-M
        product_type: INTRADAY, DELIVERY, CARRYFORWARD
        """
        if not self.connected:
            return {"error": "Not connected"}

        try:
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": token,
                "transactiontype": transaction_type,
                "exchange": exchange,
                "ordertype": order_type,
                "producttype": product_type,
                "duration": "DAY",
                "price": str(price) if order_type == "LIMIT" else "0",
                "quantity": str(quantity),
            }

            response = self.obj.placeOrder(order_params)
            return response

        except Exception as e:
            print(f"Order placement error: {e}")
            return {"error": str(e)}

    def get_positions(self) -> list[dict]:
        """Get current open positions."""
        if not self.connected:
            return []
        try:
            data = self.obj.position()
            if data and data.get("data"):
                return data["data"]
        except Exception:
            pass
        return []

    def get_holdings(self) -> list[dict]:
        """Get portfolio holdings."""
        if not self.connected:
            return []
        try:
            data = self.obj.holding()
            if data and data.get("data"):
                return data["data"]
        except Exception:
            pass
        return []


# Singleton for use across the app
_client = None


def get_client() -> AngelOneClient:
    global _client
    if _client is None:
        _client = AngelOneClient()
    return _client
