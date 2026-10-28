import sqlite3
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from dashboard import write_and_open

DB_NAME = "llc_trading_vault.db"
MIN_BARS = 60
CHART_BARS = 120


def _wilder_smooth(series: pd.Series, periods: int) -> pd.Series:
    """Wilder smoothing (RMA) used by RSI, ATR, and ADX."""
    return series.ewm(alpha=1 / periods, min_periods=periods, adjust=False).mean()


def calculate_rsi(close: pd.Series, periods: int = 14) -> pd.Series:
    """Wilder RSI — more responsive to crypto impulse than SMA-based RSI."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = _wilder_smooth(gain, periods)
    avg_loss = _wilder_smooth(loss, periods)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calculate_atr(df: pd.DataFrame, periods: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return _wilder_smooth(tr, periods)


def calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - macd_signal
    return macd, macd_signal, histogram


def calculate_adx(df: pd.DataFrame, periods: int = 14):
    """ADX + DI: trend strength and directional bias."""
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr = calculate_atr(df, periods)
    plus_di = 100 * _wilder_smooth(pd.Series(plus_dm, index=df.index), periods) / atr
    minus_di = 100 * _wilder_smooth(pd.Series(minus_dm, index=df.index), periods) / atr
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    adx = _wilder_smooth(dx, periods)
    return adx, plus_di, minus_di


def calculate_supertrend(df: pd.DataFrame, periods: int = 10, multiplier: float = 3.0) -> pd.Series:
    """ATR trailing stop that flips with trend. +1 = bullish, -1 = bearish."""
    atr = calculate_atr(df, periods).to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    hl2 = (high + low) / 2.0
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    n = len(df)
    final_upper = np.copy(basic_upper)
    final_lower = np.copy(basic_lower)
    direction = np.ones(n, dtype=int)

    for i in range(1, n):
        if np.isnan(basic_upper[i]) or np.isnan(basic_lower[i]):
            continue

        if basic_upper[i] < final_upper[i - 1] or close[i - 1] > final_upper[i - 1]:
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = final_upper[i - 1]

        if basic_lower[i] > final_lower[i - 1] or close[i - 1] < final_lower[i - 1]:
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = final_lower[i - 1]

        if close[i] <= final_lower[i]:
            direction[i] = -1
        elif close[i] >= final_upper[i]:
            direction[i] = 1
        else:
            direction[i] = direction[i - 1]

    return pd.Series(direction, index=df.index)


def add_indicators(asset_df: pd.DataFrame) -> pd.DataFrame:
    close = asset_df["close"]

    asset_df["EMA_8"] = close.ewm(span=8, adjust=False).mean()
    asset_df["EMA_21"] = close.ewm(span=21, adjust=False).mean()
    asset_df["EMA_50"] = close.ewm(span=50, adjust=False).mean()
    asset_df["SMA_20"] = close.rolling(window=20).mean()

    asset_df["RSI_14"] = calculate_rsi(close, periods=14)
    asset_df["MACD"], asset_df["MACD_SIGNAL"], asset_df["MACD_HIST"] = calculate_macd(close)
    asset_df["ADX"], asset_df["PLUS_DI"], asset_df["MINUS_DI"] = calculate_adx(asset_df)

    bb_mid = asset_df["SMA_20"]
    bb_std = close.rolling(window=20).std()
    asset_df["BB_UPPER"] = bb_mid + 2 * bb_std
    asset_df["BB_LOWER"] = bb_mid - 2 * bb_std
    asset_df["BB_WIDTH"] = (asset_df["BB_UPPER"] - asset_df["BB_LOWER"]) / bb_mid
    asset_df["BB_WIDTH_PCTL"] = asset_df["BB_WIDTH"].rolling(window=50, min_periods=20).rank(pct=True)

    asset_df["DONCHIAN_HIGH"] = asset_df["high"].rolling(window=20).max()
    asset_df["DONCHIAN_LOW"] = asset_df["low"].rolling(window=20).min()

    asset_df["VOL_SMA_20"] = asset_df["volume"].rolling(window=20).mean()
    asset_df["REL_VOLUME"] = asset_df["volume"] / asset_df["VOL_SMA_20"]

    asset_df["ROC_10"] = close.pct_change(periods=10) * 100
    asset_df["HH_20"] = close.rolling(window=20).max()
    asset_df["LL_20"] = close.rolling(window=20).min()
    asset_df["ST_DIR"] = calculate_supertrend(asset_df)

    return asset_df


def classify_regime(row) -> str:
    """Separate trending crypto from chop so RSI is not used blindly."""
    stacked_up = row["EMA_8"] > row["EMA_21"] > row["EMA_50"]
    stacked_down = row["EMA_8"] < row["EMA_21"] < row["EMA_50"]
    di_bull = row["PLUS_DI"] > row["MINUS_DI"]
    di_bear = row["MINUS_DI"] > row["PLUS_DI"]
    adx = row["ADX"]
    above_50 = row["close"] > row["EMA_50"]

    if adx >= 25:
        if stacked_up or (above_50 and di_bull):
            return "UPTREND"
        if stacked_down or ((not above_50) and di_bear):
            return "DOWNTREND"
    elif adx >= 18:
        if stacked_up and (row["ST_DIR"] == 1 or di_bull):
            return "UPTREND"
        if stacked_down and (row["ST_DIR"] == -1 or di_bear):
            return "DOWNTREND"
    return "RANGE"


def score_setup(row, prev, regime: str):
    """
    Trend-first crypto screener:
    - Uptrend: buy pullbacks to EMA21 / Donchian breakouts with volume
    - Downtrend: fade rallies into EMA21 / Donchian breakdowns
    - Range: mean-revert RSI only when ADX says there is no trend
    """
    close = row["close"]
    rsi = row["RSI_14"]
    macd_hist = row["MACD_HIST"]
    macd_cross_up = prev["MACD_HIST"] <= 0 and macd_hist > 0
    macd_cross_down = prev["MACD_HIST"] >= 0 and macd_hist < 0
    volume_expanding = row["REL_VOLUME"] >= 1.2
    squeeze = row["BB_WIDTH_PCTL"] <= 0.20
    near_ema21 = abs(close - row["EMA_21"]) / row["EMA_21"] <= 0.025
    holding_ema21 = close >= row["EMA_21"] * 0.99
    rejected_ema21 = close <= row["EMA_21"] * 1.01
    donchian_breakout = close >= row["DONCHIAN_HIGH"] * 0.998 and close > prev["close"]
    donchian_breakdown = close <= row["DONCHIAN_LOW"] * 1.002 and close < prev["close"]
    rsi_recovering = prev["RSI_14"] < 45 and rsi >= 45
    rsi_rolling_over = prev["RSI_14"] > 55 and rsi <= 55

    signals = []

    if squeeze and row["ADX"] > prev["ADX"]:
        signals.append(
            ("WATCH", "VOLATILITY SQUEEZE", "Bands compressed; ADX turning up — expansion likely.")
        )

    if regime == "UPTREND":
        if donchian_breakout and volume_expanding and macd_hist > 0:
            signals.append(
                ("BUY", "TREND BREAKOUT", "20-day high break with volume and positive MACD histogram.")
            )
        if near_ema21 and holding_ema21 and (rsi_recovering or (35 <= rsi <= 50)) and macd_hist >= prev["MACD_HIST"]:
            signals.append(
                ("BUY", "TREND PULLBACK", "Dip into rising EMA21 while structure and momentum stay bullish.")
            )
        if close > row["EMA_8"] > row["EMA_21"] and macd_cross_up and rsi > 50:
            signals.append(
                ("BUY", "MOMENTUM RECLAIM", "MACD flipped positive inside an established uptrend.")
            )

    elif regime == "DOWNTREND":
        if donchian_breakdown and volume_expanding and macd_hist < 0:
            signals.append(
                ("SELL", "TREND BREAKDOWN", "20-day low break with volume and negative MACD histogram.")
            )
        if near_ema21 and rejected_ema21 and (rsi_rolling_over or (50 <= rsi <= 65)) and macd_hist <= prev["MACD_HIST"]:
            signals.append(
                ("SELL", "TREND RALLY FADE", "Bounce into falling EMA21 while structure stays bearish.")
            )
        if close < row["EMA_8"] < row["EMA_21"] and macd_cross_down and rsi < 50:
            signals.append(
                ("SELL", "MOMENTUM BREAK", "MACD flipped negative inside an established downtrend.")
            )

    else:
        if rsi < 32 and close <= row["BB_LOWER"] * 1.01:
            signals.append(
                ("BUY", "RANGE OVERSOLD", "Mean-reversion long: RSI washed out at lower Bollinger band.")
            )
        elif rsi > 68 and close >= row["BB_UPPER"] * 0.99:
            signals.append(
                ("SELL", "RANGE OVERBOUGHT", "Mean-reversion short: RSI extended at upper Bollinger band.")
            )

    if not signals:
        if regime == "UPTREND":
            signals.append(
                ("HOLD", "WAIT PULLBACK", "Uptrend intact. Wait for a dip into EMA21 with RSI reset, or a volume breakout.")
            )
        elif regime == "DOWNTREND":
            signals.append(
                ("HOLD", "WAIT RALLY", "Downtrend intact. Do not buy oversold. Wait for a bounce into EMA21 or a volume breakdown.")
            )
        else:
            signals.append(("HOLD", "NO EDGE", "Chop. Only fade RSI extremes at Bollinger bands."))

    priority = {"BUY": 0, "SELL": 1, "WATCH": 2, "HOLD": 3}
    signals.sort(key=lambda s: priority[s[0]])
    return signals[0]


def _clean_num(value):
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return float(value) if isinstance(value, (int, float)) else value


def _series_payload(asset_df: pd.DataFrame) -> dict:
    tail = asset_df.tail(CHART_BARS).copy()
    dates = pd.to_datetime(tail["timestamp"], unit="s", utc=True).dt.strftime("%Y-%m-%d").tolist()

    def col(name):
        return [_clean_num(v) for v in tail[name].tolist()]

    return {
        "dates": dates,
        "close": col("close"),
        "ema21": col("EMA_21"),
        "ema50": col("EMA_50"),
        "bb_upper": col("BB_UPPER"),
        "bb_lower": col("BB_LOWER"),
        "rsi": col("RSI_14"),
        "macd_hist": col("MACD_HIST"),
        "adx": col("ADX"),
    }


def _next_step(action: str, regime: str) -> str:
    if action == "BUY":
        return "Valid buy setup. Size the trade only if it still matches the live candle."
    if action == "SELL":
        return "Valid sell/fade setup. Do not flip this into a buy."
    if regime == "DOWNTREND":
        return "Do not buy. Wait for a bounce into EMA21 to fade, a volume breakdown, or a full regime flip to UPTREND."
    if regime == "UPTREND":
        return "Trend is up, but there is no entry yet. Wait for a dip into EMA21 or a volume breakout."
    return "No trend and no extreme. Stand aside until RSI hits a Bollinger extreme or a trend forms."


def collect_scan() -> dict:
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM historical_ohlcv ORDER BY timestamp ASC;", conn)
    conn.close()

    numeric_cols = ["open", "high", "low", "close", "volume", "timestamp"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["ticker", "timestamp", "close"]).sort_values(["ticker", "timestamp"])

    assets = []
    for ticker in df["ticker"].unique():
        asset_df = df[df["ticker"] == ticker].copy().reset_index(drop=True)
        if len(asset_df) < MIN_BARS:
            print(f"⚠️ {ticker}: Not enough data history to screen ({len(asset_df)} < {MIN_BARS} bars).")
            print("-" * 78)
            continue

        asset_df = add_indicators(asset_df)
        latest = asset_df.iloc[-1]
        prev = asset_df.iloc[-2]

        if pd.isna(latest["EMA_50"]) or pd.isna(latest["ADX"]) or pd.isna(latest["RSI_14"]):
            print(f"⚠️ {ticker}: Indicators still warming up.")
            print("-" * 78)
            continue

        regime = classify_regime(latest)
        action, setup, reason = score_setup(latest, prev, regime)
        assets.append(
            {
                "ticker": ticker,
                "action": action,
                "setup": setup,
                "reason": reason,
                "next_step": _next_step(action, regime),
                "regime": regime,
                "close": _clean_num(latest["close"]),
                "rsi": _clean_num(latest["RSI_14"]),
                "adx": _clean_num(latest["ADX"]),
                "ema21": _clean_num(latest["EMA_21"]),
                "ema50": _clean_num(latest["EMA_50"]),
                "rel_volume": _clean_num(latest["REL_VOLUME"]),
                "roc": _clean_num(latest["ROC_10"]),
                "macd_hist": _clean_num(latest["MACD_HIST"]),
                "st_label": "BULL" if latest["ST_DIR"] == 1 else "BEAR",
                "series": _series_payload(asset_df),
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "assets": assets,
    }


def run_screener(open_dashboard: bool = True):
    print("🌅 5:00 AM PST ALGORITHMIC MARKET SCREENER")
    print("Trend-first crypto scan: EMA stack + Supertrend + ADX regime,")
    print("then pullback / breakout / squeeze confirmation with RSI, MACD, volume.")
    print("=" * 78)

    scan = collect_scan()
    ranked = scan["assets"]

    for row in ranked:
        ticker = row["ticker"]
        print(
            f"[{ticker}] Close: ${row['close']:,.2f} | RSI: {row['rsi']:.1f} | ADX: {row['adx']:.1f} | "
            f"EMA21: ${row['ema21']:,.2f} | EMA50: ${row['ema50']:,.2f}"
        )
        print(
            f"   Regime: {row['regime']:9} | Supertrend: {row['st_label']} | 10d ROC: {row['roc']:+.1f}% | "
            f"RelVol: {row['rel_volume']:.2f}x | MACD hist: {row['macd_hist']:+.4f}"
        )
        print(f"   {row['action']} | {row['setup']}: {row['reason']}")
        print("-" * 78)

    actionable = [r for r in ranked if r["action"] in {"BUY", "SELL"}]
    print("WATCHLIST PRIORITY")
    print("=" * 78)
    if not actionable:
        print("No trend-aligned BUY/SELL setups today. Wait for pullback, breakout, or squeeze expansion.")
    else:
        order = {"BUY": 0, "SELL": 1}
        actionable.sort(key=lambda r: (order[r["action"]], -r["adx"]))
        for r in actionable:
            print(
                f"  {r['action']:4} {r['ticker']:8} {r['setup']:18} "
                f"regime={r['regime']} ADX={r['adx']:.1f} RSI={r['rsi']:.1f} ROC10={r['roc']:+.1f}%"
            )

    if open_dashboard:
        write_and_open(scan)

    return scan


if __name__ == "__main__":
    run_screener()
