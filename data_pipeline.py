import sqlite3
import pandas as pd
from kraken.spot import Market

# 1. Initialize Kraken Public Market Client
client = Market()

# 2. Setup Local Data Storage Path
DB_NAME = "llc_trading_vault.db"
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Create structured table optimized for time-series crypto candlesticks
# Note the PRIMARY KEY constraint which prevents duplicates
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

def fetch_and_save_data(target_pair="BTCUSD"):
    """Fetches daily historical candles from Kraken Pro and inserts/updates local SQLite DB."""
    print(f"[{target_pair}] Requesting historical daily candles from Kraken API...")
    
    try:
        # Retrieve daily (1440 minutes) OHLC data
        response = client.get_ohlc(pair=target_pair, interval=1440)
        
        # 1. Safely handle Kraken's weird alternative legacy dictionary naming conventions
        if target_pair in response:
            candles = response[target_pair]
        elif target_pair == "BTCUSD" and "XXBTZUSD" in response:
            candles = response["XXBTZUSD"]
        elif target_pair == "ETHUSD" and "XETHZUSD" in response:
            candles = response["XETHZUSD"]
        else:
            # Fallback to grabbing the first data dictionary key that isn't 'last'
            available_keys = [k for k in response.keys() if k != 'last']
            candles = response[available_keys[0]] if available_keys else []
            
        if not candles:
            print(f"⚠️ No data returned for pair: {target_pair}")
            return
            
        # Convert raw API response array into a clean Dataframe
        df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        df['ticker'] = target_pair
        
        # Format columns exactly to match our database schema
        db_df = df[['ticker', 'time', 'open', 'high', 'low', 'close', 'volume']].copy()
        db_df.columns = ['ticker', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        # 🌟 THE CORRECT FIX: Use 'append' but force SQLite to overwrite matching primary keys
        # This keeps all assets together but cleanly replaces old duplicate days with fresh data
        struct_query = """
            INSERT OR REPLACE INTO historical_ohlcv (ticker, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(struct_query, db_df.values.tolist())
        conn.commit()
        
        print(f"✅ Success! Processed {len(db_df)} clean records for {target_pair} into database.")
        
    except Exception as e:
        print(f"❌ Network or processing error for {target_pair}: {e}")

if __name__ == "__main__":
    watchlist = ["BTCUSD", "ETHUSD", "SOLUSD"]
    for asset in watchlist:
        fetch_and_save_data(asset)
    
    conn.close()
    print("\n🏁 Pipeline execution finished successfully.")
