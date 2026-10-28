import sqlite3
import pandas as pd
import yfinance as yf
from kraken.spot import Market

# ---------------------------------------------------------------
# Data sources
#   Crypto -> Kraken public API (python-kraken-sdk)
#   US stocks -> Yahoo Finance (yfinance). Kraken's public API does not
#   serve US-listed equities, and its tokenized xStocks are not offered
#   to US residents.
# ---------------------------------------------------------------
client = Market()

# Local Data Storage Path
DB_NAME = "llc_trading_vault.db"
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Structured table for time-series candlesticks.
# PRIMARY KEY (ticker, timestamp) prevents duplicate days.
cursor.execute('''
    CREATE TABLE IF NOT EXISTS historical_ohlcv (
        ticker TEXT,
        timestamp INTEGER,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        PRIMARY KEY (ticker, timestamp)
    )
''')
conn.commit()

UPSERT_SQL = """
    INSERT OR REPLACE INTO historical_ohlcv (ticker, timestamp, open, high, low, close, volume)
    VALUES (?, ?, ?, ?, ?, ?, ?)
"""


def save_to_db(db_df, label):
    """Casts types and upserts a [ticker, timestamp, open, high, low, close, volume] frame."""
    for col in ['open', 'high', 'low', 'close', 'volume']:
        db_df[col] = db_df[col].astype(float)
    db_df['timestamp'] = db_df['timestamp'].astype(int)

    cursor.executemany(UPSERT_SQL, db_df.values.tolist())
    conn.commit()
    print(f"✅ Success! Processed {len(db_df)} clean records for {label} into database.")


# ---------------------------------------------------------------
# Crypto (Kraken)
# ---------------------------------------------------------------
def fetch_crypto(target_pair="BTCUSD"):
    """Fetches daily candles from Kraken (max 720 most recent)."""
    print(f"[{target_pair}] Requesting daily candles from Kraken API...")
    try:
        response = client.get_ohlc(pair=target_pair, interval=1440)

        # Handle Kraken's legacy pair-key naming (e.g. XXBTZUSD)
        if target_pair in response:
            candles = response[target_pair]
        elif target_pair == "BTCUSD" and "XXBTZUSD" in response:
            candles = response["XXBTZUSD"]
        elif target_pair == "ETHUSD" and "XETHZUSD" in response:
            candles = response["XETHZUSD"]
        else:
            available_keys = [k for k in response.keys() if k != 'last']
            candles = response[available_keys[0]] if available_keys else []

        if not candles:
            print(f"⚠️ No data returned for pair: {target_pair}")
            return

        df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        df['ticker'] = target_pair

        db_df = df[['ticker', 'time', 'open', 'high', 'low', 'close', 'volume']].copy()
        db_df.columns = ['ticker', 'timestamp', 'open', 'high', 'low', 'close', 'volume']

        # Kraken's last candle is the current, unfinished day -> drop it
        db_df = db_df.iloc[:-1].copy()

        save_to_db(db_df, target_pair)

    except Exception as e:
        print(f"❌ Network or processing error for {target_pair}: {e}")


# ---------------------------------------------------------------
# US stocks (Yahoo Finance)
# ---------------------------------------------------------------
def fetch_stock(ticker="AAPL", period="5y", adjusted=True):
    """
    Fetches daily candles for a US-listed stock from Yahoo Finance.

    period   : '1y', '5y', 'max', ...
    adjusted : True  -> prices adjusted for splits & dividends (best for returns)
               False -> raw traded prices (match your brokerage statements)
    """
    print(f"[{ticker}] Requesting daily candles from Yahoo Finance...")
    try:
        hist = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=adjusted)

        if hist.empty:
            print(f"⚠️ No data returned for ticker: {ticker}")
            return

        hist = hist.reset_index()

        # Yahoo dates are New York-local midnights. Re-stamp each trading day
        # as 00:00 UTC so stock rows share the same daily timestamps as
        # Kraken's crypto candles and can be joined on (timestamp).
        # Computed as (date - epoch) / 1 second so the result is correct whatever
        # internal resolution pandas uses (ns in pandas 2, s in pandas 3).
        trade_dates = pd.to_datetime(hist['Date'].dt.date).dt.tz_localize("UTC")
        epoch = pd.Timestamp("1970-01-01", tz="UTC")
        hist['timestamp'] = (trade_dates - epoch) // pd.Timedelta("1s")

        db_df = pd.DataFrame({
            'ticker': ticker,
            'timestamp': hist['timestamp'],
            'open': hist['Open'],
            'high': hist['High'],
            'low': hist['Low'],
            'close': hist['Close'],
            'volume': hist['Volume'],
        })

        save_to_db(db_df, ticker)

    except Exception as e:
        print(f"❌ Network or processing error for {ticker}: {e}")


if __name__ == "__main__":
    crypto_watchlist = ["BTCUSD", "ETHUSD", "SOLUSD"]
    stock_watchlist = ["AMD", "IONQ", "CRML", "AAPL"]

    for pair in crypto_watchlist:
        fetch_crypto(pair)

    for ticker in stock_watchlist:
        fetch_stock(ticker, period="5y", adjusted=True)

    conn.close()
    print("\n🏁 Pipeline execution finished.")