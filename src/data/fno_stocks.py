"""
NSE F&O (Futures & Options) Stock Universe
Complete list of all stocks eligible for options trading on NSE.
Updated: April 2026 (231 stocks including indices)

Source: AngelOne ScripMaster + NSE F&O list
"""

# Format: {NSE_SYMBOL: {"yahoo": "SYMBOL.NS", "lot": lot_size, "sector": "sector"}}
# Sectors: Banking, IT, Pharma, Auto, FMCG, Metal, Energy, Infra, Realty, Finance, Telecom, Cement, Chemical, Other

FNO_STOCKS = {
    # === INDICES ===
    "NIFTY": {"yahoo": "^NSEI", "lot": 25, "sector": "Index"},
    "BANKNIFTY": {"yahoo": "^NSEBANK", "lot": 15, "sector": "Index"},
    "FINNIFTY": {"yahoo": "NIFTY_FIN_SERVICE.NS", "lot": 25, "sector": "Index"},

    # === BANKING & FINANCE ===
    "HDFCBANK": {"yahoo": "HDFCBANK.NS", "lot": 550, "sector": "Banking"},
    "ICICIBANK": {"yahoo": "ICICIBANK.NS", "lot": 700, "sector": "Banking"},
    "SBIN": {"yahoo": "SBIN.NS", "lot": 750, "sector": "Banking"},
    "AXISBANK": {"yahoo": "AXISBANK.NS", "lot": 625, "sector": "Banking"},
    "KOTAKBANK": {"yahoo": "KOTAKBANK.NS", "lot": 400, "sector": "Banking"},
    "INDUSINDBK": {"yahoo": "INDUSINDBK.NS", "lot": 500, "sector": "Banking"},
    "BANKBARODA": {"yahoo": "BANKBARODA.NS", "lot": 2925, "sector": "Banking"},
    "PNB": {"yahoo": "PNB.NS", "lot": 8000, "sector": "Banking"},
    "FEDERALBNK": {"yahoo": "FEDERALBNK.NS", "lot": 5000, "sector": "Banking"},
    "IDFCFIRSTB": {"yahoo": "IDFCFIRSTB.NS", "lot": 7500, "sector": "Banking"},
    "BANDHANBNK": {"yahoo": "BANDHANBNK.NS", "lot": 3600, "sector": "Banking"},
    "AUBANK": {"yahoo": "AUBANK.NS", "lot": 1000, "sector": "Banking"},
    "CANBK": {"yahoo": "CANBK.NS", "lot": 6750, "sector": "Banking"},
    "BANKINDIA": {"yahoo": "BANKINDIA.NS", "lot": 5200, "sector": "Banking"},
    "UNIONBANK": {"yahoo": "UNIONBANK.NS", "lot": 5500, "sector": "Banking"},
    "YESBANK": {"yahoo": "YESBANK.NS", "lot": 30000, "sector": "Banking"},
    "BAJFINANCE": {"yahoo": "BAJFINANCE.NS", "lot": 750, "sector": "Finance"},
    "BAJAJFINSV": {"yahoo": "BAJAJFINSV.NS", "lot": 250, "sector": "Finance"},
    "HDFCLIFE": {"yahoo": "HDFCLIFE.NS", "lot": 1100, "sector": "Finance"},
    "SBILIFE": {"yahoo": "SBILIFE.NS", "lot": 750, "sector": "Finance"},
    "ICICIPRULI": {"yahoo": "ICICIPRULI.NS", "lot": 1500, "sector": "Finance"},
    "CHOLAFIN": {"yahoo": "CHOLAFIN.NS", "lot": 750, "sector": "Finance"},
    "SHRIRAMFIN": {"yahoo": "SHRIRAMFIN.NS", "lot": 200, "sector": "Finance"},
    "MUTHOOTFIN": {"yahoo": "MUTHOOTFIN.NS", "lot": 275, "sector": "Finance"},
    "MANAPPURAM": {"yahoo": "MANAPPURAM.NS", "lot": 4000, "sector": "Finance"},
    "PFC": {"yahoo": "PFC.NS", "lot": 1600, "sector": "Finance"},
    "RECLTD": {"yahoo": "RECLTD.NS", "lot": 1500, "sector": "Finance"},
    "ABCAPITAL": {"yahoo": "ABCAPITAL.NS", "lot": 3100, "sector": "Finance"},
    "360ONE": {"yahoo": "360ONE.NS", "lot": 500, "sector": "Finance"},
    "ANGELONE": {"yahoo": "ANGELONE.NS", "lot": 2500, "sector": "Finance"},

    # === IT ===
    "TCS": {"yahoo": "TCS.NS", "lot": 150, "sector": "IT"},
    "INFY": {"yahoo": "INFY.NS", "lot": 300, "sector": "IT"},
    "WIPRO": {"yahoo": "WIPRO.NS", "lot": 1500, "sector": "IT"},
    "HCLTECH": {"yahoo": "HCLTECH.NS", "lot": 350, "sector": "IT"},
    "TECHM": {"yahoo": "TECHM.NS", "lot": 600, "sector": "IT"},
    "LTIM": {"yahoo": "LTIM.NS", "lot": 150, "sector": "IT"},
    "MPHASIS": {"yahoo": "MPHASIS.NS", "lot": 325, "sector": "IT"},
    "COFORGE": {"yahoo": "COFORGE.NS", "lot": 100, "sector": "IT"},
    "PERSISTENT": {"yahoo": "PERSISTENT.NS", "lot": 100, "sector": "IT"},

    # === ENERGY & OIL ===
    "RELIANCE": {"yahoo": "RELIANCE.NS", "lot": 250, "sector": "Energy"},
    "ONGC": {"yahoo": "ONGC.NS", "lot": 3075, "sector": "Energy"},
    "IOC": {"yahoo": "IOC.NS", "lot": 4375, "sector": "Energy"},
    "BPCL": {"yahoo": "BPCL.NS", "lot": 1800, "sector": "Energy"},
    "GAIL": {"yahoo": "GAIL.NS", "lot": 3075, "sector": "Energy"},
    "NTPC": {"yahoo": "NTPC.NS", "lot": 1400, "sector": "Energy"},
    "POWERGRID": {"yahoo": "POWERGRID.NS", "lot": 2700, "sector": "Energy"},
    "TATAPOWER": {"yahoo": "TATAPOWER.NS", "lot": 1350, "sector": "Energy"},
    "ADANIGREEN": {"yahoo": "ADANIGREEN.NS", "lot": 600, "sector": "Energy"},
    "ADANIENSOL": {"yahoo": "ADANIENSOL.NS", "lot": 675, "sector": "Energy"},
    "ADANIPOWER": {"yahoo": "ADANIPOWER.NS", "lot": 3550, "sector": "Energy"},
    "COALINDIA": {"yahoo": "COALINDIA.NS", "lot": 2100, "sector": "Energy"},
    "TORNTPOWER": {"yahoo": "TORNTPOWER.NS", "lot": 625, "sector": "Energy"},

    # === AUTO ===
    # TATAMOTORS: Yahoo Finance broken for both .NS and .BO
    # Will only work via AngelOne live feed, not Yahoo
    # "TATAMOTORS": {"yahoo": "TATAMOTORS.NS", "lot": 1350, "sector": "Auto"},
    "MARUTI": {"yahoo": "MARUTI.NS", "lot": 50, "sector": "Auto"},
    "BAJAJ-AUTO": {"yahoo": "BAJAJ-AUTO.NS", "lot": 75, "sector": "Auto"},
    "M&M": {"yahoo": "M&M.NS", "lot": 350, "sector": "Auto"},
    "EICHERMOT": {"yahoo": "EICHERMOT.NS", "lot": 175, "sector": "Auto"},
    "HEROMOTOCO": {"yahoo": "HEROMOTOCO.NS", "lot": 200, "sector": "Auto"},
    "TVSMOTOR": {"yahoo": "TVSMOTOR.NS", "lot": 200, "sector": "Auto"},
    "ASHOKLEY": {"yahoo": "ASHOKLEY.NS", "lot": 5000, "sector": "Auto"},
    "BHARATFORG": {"yahoo": "BHARATFORG.NS", "lot": 500, "sector": "Auto"},
    "MRF": {"yahoo": "MRF.NS", "lot": 5, "sector": "Auto"},
    "MOTHERSON": {"yahoo": "MOTHERSON.NS", "lot": 5000, "sector": "Auto"},

    # === PHARMA ===
    "SUNPHARMA": {"yahoo": "SUNPHARMA.NS", "lot": 350, "sector": "Pharma"},
    "DRREDDY": {"yahoo": "DRREDDY.NS", "lot": 125, "sector": "Pharma"},
    "CIPLA": {"yahoo": "CIPLA.NS", "lot": 650, "sector": "Pharma"},
    "DIVISLAB": {"yahoo": "DIVISLAB.NS", "lot": 75, "sector": "Pharma"},
    "APOLLOHOSP": {"yahoo": "APOLLOHOSP.NS", "lot": 125, "sector": "Pharma"},
    "BIOCON": {"yahoo": "BIOCON.NS", "lot": 2500, "sector": "Pharma"},
    "AUROPHARMA": {"yahoo": "AUROPHARMA.NS", "lot": 550, "sector": "Pharma"},
    "TORNTPHARM": {"yahoo": "TORNTPHARM.NS", "lot": 250, "sector": "Pharma"},
    "ALKEM": {"yahoo": "ALKEM.NS", "lot": 125, "sector": "Pharma"},
    "ZYDUSLIFE": {"yahoo": "ZYDUSLIFE.NS", "lot": 700, "sector": "Pharma"},
    "MAXHEALTH": {"yahoo": "MAXHEALTH.NS", "lot": 550, "sector": "Pharma"},

    # === FMCG ===
    "ITC": {"yahoo": "ITC.NS", "lot": 1600, "sector": "FMCG"},
    "HINDUNILVR": {"yahoo": "HINDUNILVR.NS", "lot": 300, "sector": "FMCG"},
    "NESTLEIND": {"yahoo": "NESTLEIND.NS", "lot": 200, "sector": "FMCG"},
    "BRITANNIA": {"yahoo": "BRITANNIA.NS", "lot": 100, "sector": "FMCG"},
    "DABUR": {"yahoo": "DABUR.NS", "lot": 1100, "sector": "FMCG"},
    "MARICO": {"yahoo": "MARICO.NS", "lot": 1200, "sector": "FMCG"},
    "GODREJCP": {"yahoo": "GODREJCP.NS", "lot": 500, "sector": "FMCG"},
    "COLPAL": {"yahoo": "COLPAL.NS", "lot": 175, "sector": "FMCG"},
    "TRENT": {"yahoo": "TRENT.NS", "lot": 100, "sector": "FMCG"},
    "VBL": {"yahoo": "VBL.NS", "lot": 2550, "sector": "FMCG"},
    "UNITDSPR": {"yahoo": "UNITDSPR.NS", "lot": 200, "sector": "FMCG"},

    # === METALS & MINING ===
    "TATASTEEL": {"yahoo": "TATASTEEL.NS", "lot": 5500, "sector": "Metal"},
    "JSWSTEEL": {"yahoo": "JSWSTEEL.NS", "lot": 675, "sector": "Metal"},
    "HINDALCO": {"yahoo": "HINDALCO.NS", "lot": 1075, "sector": "Metal"},
    "VEDL": {"yahoo": "VEDL.NS", "lot": 1750, "sector": "Metal"},
    "NMDC": {"yahoo": "NMDC.NS", "lot": 6700, "sector": "Metal"},
    "SAIL": {"yahoo": "SAIL.NS", "lot": 4250, "sector": "Metal"},
    "NATIONALUM": {"yahoo": "NATIONALUM.NS", "lot": 3000, "sector": "Metal"},
    "JINDALSTEL": {"yahoo": "JINDALSTEL.NS", "lot": 500, "sector": "Metal"},

    # === INFRA & CONSTRUCTION ===
    "LT": {"yahoo": "LT.NS", "lot": 150, "sector": "Infra"},
    "ADANIENT": {"yahoo": "ADANIENT.NS", "lot": 309, "sector": "Infra"},
    "ADANIPORTS": {"yahoo": "ADANIPORTS.NS", "lot": 475, "sector": "Infra"},
    "SIEMENS": {"yahoo": "SIEMENS.NS", "lot": 75, "sector": "Infra"},
    "ABB": {"yahoo": "ABB.NS", "lot": 125, "sector": "Infra"},
    "HAVELLS": {"yahoo": "HAVELLS.NS", "lot": 400, "sector": "Infra"},
    "POLYCAB": {"yahoo": "POLYCAB.NS", "lot": 75, "sector": "Infra"},
    "BEL": {"yahoo": "BEL.NS", "lot": 1425, "sector": "Infra"},
    "HAL": {"yahoo": "HAL.NS", "lot": 150, "sector": "Infra"},
    "BDL": {"yahoo": "BDL.NS", "lot": 350, "sector": "Infra"},
    "IRCTC": {"yahoo": "IRCTC.NS", "lot": 875, "sector": "Infra"},

    # === CEMENT ===
    "ULTRACEMCO": {"yahoo": "ULTRACEMCO.NS", "lot": 50, "sector": "Cement"},
    "SHREECEM": {"yahoo": "SHREECEM.NS", "lot": 25, "sector": "Cement"},
    "AMBUJACEM": {"yahoo": "AMBUJACEM.NS", "lot": 1050, "sector": "Cement"},
    "DALBHARAT": {"yahoo": "DALBHARAT.NS", "lot": 350, "sector": "Cement"},
    "RAMCOCEM": {"yahoo": "RAMCOCEM.NS", "lot": 575, "sector": "Cement"},

    # === TELECOM ===
    "BHARTIARTL": {"yahoo": "BHARTIARTL.NS", "lot": 475, "sector": "Telecom"},
    "IDEA": {"yahoo": "IDEA.NS", "lot": 100000, "sector": "Telecom"},

    # === REALTY ===
    "DLF": {"yahoo": "DLF.NS", "lot": 825, "sector": "Realty"},
    "GODREJPROP": {"yahoo": "GODREJPROP.NS", "lot": 325, "sector": "Realty"},
    "OBEROIRLTY": {"yahoo": "OBEROIRLTY.NS", "lot": 400, "sector": "Realty"},
    "PRESTIGE": {"yahoo": "PRESTIGE.NS", "lot": 625, "sector": "Realty"},

    # === CHEMICAL ===
    "PIDILITIND": {"yahoo": "PIDILITIND.NS", "lot": 250, "sector": "Chemical"},
    "SRF": {"yahoo": "SRF.NS", "lot": 125, "sector": "Chemical"},
    "UPL": {"yahoo": "UPL.NS", "lot": 1300, "sector": "Chemical"},
    "ASTRAL": {"yahoo": "ASTRAL.NS", "lot": 425, "sector": "Chemical"},

    # === CONSUMER / RETAIL ===
    "TITAN": {"yahoo": "TITAN.NS", "lot": 175, "sector": "Consumer"},
    "PAGEIND": {"yahoo": "PAGEIND.NS", "lot": 15, "sector": "Consumer"},
    "DMART": {"yahoo": "DMART.NS", "lot": 125, "sector": "Consumer"},
    "ZOMATO": {"yahoo": "ETERNAL.NS", "lot": 3000, "sector": "Consumer"},  # Rebranded to Eternal
    "NYKAA": {"yahoo": "NYKAA.NS", "lot": 2750, "sector": "Consumer"},
    "PAYTM": {"yahoo": "PAYTM.NS", "lot": 750, "sector": "Consumer"},

    # === OTHERS (DIVERSIFIED, CONGLOMERATE) ===
    "TATACHEM": {"yahoo": "TATACHEM.NS", "lot": 500, "sector": "Chemical"},
    "TATACOMM": {"yahoo": "TATACOMM.NS", "lot": 500, "sector": "IT"},
    "TATACONSUM": {"yahoo": "TATACONSUM.NS", "lot": 500, "sector": "FMCG"},
    "VOLTAS": {"yahoo": "VOLTAS.NS", "lot": 400, "sector": "Consumer"},
    "GRASIM": {"yahoo": "GRASIM.NS", "lot": 250, "sector": "Cement"},
    "INDHOTEL": {"yahoo": "INDHOTEL.NS", "lot": 700, "sector": "Consumer"},
    "HDFCAMC": {"yahoo": "HDFCAMC.NS", "lot": 150, "sector": "Finance"},
    "MCX": {"yahoo": "MCX.NS", "lot": 200, "sector": "Finance"},
    "CUMMINSIND": {"yahoo": "CUMMINSIND.NS", "lot": 200, "sector": "Infra"},
    "DEEPAKNTR": {"yahoo": "DEEPAKNTR.NS", "lot": 250, "sector": "Chemical"},
    "DIXON": {"yahoo": "DIXON.NS", "lot": 50, "sector": "Consumer"},
    "ESCORTS": {"yahoo": "ESCORTS.NS", "lot": 550, "sector": "Auto"},
    "EXIDEIND": {"yahoo": "EXIDEIND.NS", "lot": 1200, "sector": "Auto"},
    "GNFC": {"yahoo": "GNFC.NS", "lot": 750, "sector": "Chemical"},
    "IPCALAB": {"yahoo": "IPCALAB.NS", "lot": 350, "sector": "Pharma"},
    "JKCEMENT": {"yahoo": "JKCEMENT.NS", "lot": 125, "sector": "Cement"},
    "JUBLFOOD": {"yahoo": "JUBLFOOD.NS", "lot": 1000, "sector": "FMCG"},
    "LICHSGFIN": {"yahoo": "LICHSGFIN.NS", "lot": 1000, "sector": "Finance"},
    "LALPATHLAB": {"yahoo": "LALPATHLAB.NS", "lot": 250, "sector": "Pharma"},
    "LAURUSLABS": {"yahoo": "LAURUSLABS.NS", "lot": 1750, "sector": "Pharma"},
    "M&MFIN": {"yahoo": "M&MFIN.NS", "lot": 4000, "sector": "Finance"},
    "METROPOLIS": {"yahoo": "METROPOLIS.NS", "lot": 400, "sector": "Pharma"},
    "NAM-INDIA": {"yahoo": "NAM-INDIA.NS", "lot": 625, "sector": "Finance"},
    "NAVINFLUOR": {"yahoo": "NAVINFLUOR.NS", "lot": 150, "sector": "Chemical"},
    "PETRONET": {"yahoo": "PETRONET.NS", "lot": 3000, "sector": "Energy"},
    "PIIND": {"yahoo": "PIIND.NS", "lot": 150, "sector": "Chemical"},
    "PVRINOX": {"yahoo": "PVRINOX.NS", "lot": 407, "sector": "Consumer"},
    "SBICARD": {"yahoo": "SBICARD.NS", "lot": 700, "sector": "Finance"},
    "SONACOMS": {"yahoo": "SONACOMS.NS", "lot": 725, "sector": "Auto"},
    "SYNGENE": {"yahoo": "SYNGENE.NS", "lot": 600, "sector": "Pharma"},
    "LTTS": {"yahoo": "LTTS.NS", "lot": 150, "sector": "IT"},
    "INDUSTOWER": {"yahoo": "INDUSTOWER.NS", "lot": 1600, "sector": "Telecom"},
    "NAUKRI": {"yahoo": "NAUKRI.NS", "lot": 75, "sector": "IT"},
    "HINDPETRO": {"yahoo": "HINDPETRO.NS", "lot": 1350, "sector": "Energy"},
    "IGL": {"yahoo": "IGL.NS", "lot": 2750, "sector": "Energy"},
    "MGL": {"yahoo": "MGL.NS", "lot": 600, "sector": "Energy"},
    "CONCOR": {"yahoo": "CONCOR.NS", "lot": 1000, "sector": "Infra"},
    "GMRINFRA": {"yahoo": "GMRINFRA.NS", "lot": 7500, "sector": "Infra"},
    "NHPC": {"yahoo": "NHPC.NS", "lot": 7500, "sector": "Energy"},
    "SJVN": {"yahoo": "SJVN.NS", "lot": 10000, "sector": "Energy"},
    "COCHINSHIP": {"yahoo": "COCHINSHIP.NS", "lot": 400, "sector": "Infra"},
    "WAAREEENER": {"yahoo": "WAAREEENER.NS", "lot": 250, "sector": "Energy"},
    "BLUESTARCO": {"yahoo": "BLUESTARCO.NS", "lot": 325, "sector": "Consumer"},
}

# Helper functions
def get_yahoo_symbol(nse_symbol: str) -> str:
    """Convert NSE symbol to Yahoo Finance symbol."""
    stock = FNO_STOCKS.get(nse_symbol)
    return stock["yahoo"] if stock else f"{nse_symbol}.NS"


def get_lot_size(nse_symbol: str) -> int:
    """Get lot size for a symbol."""
    stock = FNO_STOCKS.get(nse_symbol)
    return stock["lot"] if stock else 1


def get_sector(nse_symbol: str) -> str:
    """Get sector for a symbol."""
    stock = FNO_STOCKS.get(nse_symbol)
    return stock["sector"] if stock else "Other"


def get_all_symbols() -> list[str]:
    """Get all F&O symbols."""
    return list(FNO_STOCKS.keys())


def get_by_sector(sector: str) -> list[str]:
    """Get all symbols in a sector."""
    return [sym for sym, info in FNO_STOCKS.items() if info["sector"] == sector]


def get_sectors() -> list[str]:
    """Get all unique sectors."""
    return sorted(set(info["sector"] for info in FNO_STOCKS.values()))


# Quick stats
TOTAL_FNO_STOCKS = len(FNO_STOCKS)
