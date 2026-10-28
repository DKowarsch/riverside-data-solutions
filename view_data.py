import sqlite3
import pandas as pd

# Connect to your local database vault
conn = sqlite3.connect("llc_trading_vault.db")

# Fetch total row count to verify data size
count_df = pd.read_sql_query("SELECT COUNT(*) as total_rows FROM historical_ohlcv;", conn)
print("DATABASE HEALTH CHECK")
print("=============================")
print(f"Total rows collected: {count_df['total_rows'].iloc[0]}")
print("=============================\n")

# Print the 10 most recent data rows saved
print("LATEST 10 DATA ROWS IN VAULT:")
print("--------------------------------------------------------------------------------")
query = "SELECT * FROM historical_ohlcv ORDER BY timestamp DESC LIMIT 10;"
df = pd.read_sql_query(query, conn)

# Convert Unix timestamp to readable date strings
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
print(df.to_string(index=False))

conn.close()
