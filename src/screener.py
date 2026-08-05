"""
核心篩選邏輯:
  條件1:最近 N 個交易日內,曾出現「收盤價相對15MA乖離率 >= BIAS_THRESHOLD%」
  條件2:最新一根還原日K收盤價 > SMA87

還原日K:使用 yfinance auto_adjust=True,會依除權息回推調整 OHLC。
"""
from __future__ import annotations
import time
import pandas as pd
import yfinance as yf

# ------- 可調參數 -------
LOOKBACK_DAYS = 10        # 「10個交易日內」
BIAS_MA_PERIOD = 15       # 15MA
BIAS_THRESHOLD = 20.0     # 乖離 20%
LONG_MA_PERIOD = 87       # SMA87
BIAS_DIRECTION = "both"   # "up"=只抓正乖離(急漲) / "down"=只抓負乖離(急跌) / "both"=兩者都抓
HISTORY_PERIOD = "1y"     # 抓多久的歷史資料來算 MA(87MA需要至少87根+緩衝)
REQUEST_SLEEP = 0.3       # 每檔股票間的延遲,避免被限流
# ------------------------


def fetch_history(ticker: str) -> pd.DataFrame | None:
    try:
        df = yf.Ticker(ticker).history(period=HISTORY_PERIOD, auto_adjust=True)
        if df is None or df.empty or len(df) < LONG_MA_PERIOD + 5:
            return None
        return df
    except Exception:
        return None


def evaluate(ticker: str, name: str) -> dict | None:
    """回傳符合條件的股票資訊,不符合則回傳 None"""
    df = fetch_history(ticker)
    if df is None:
        return None

    close = df["Close"]
    ma15 = close.rolling(BIAS_MA_PERIOD).mean()
    ma87 = close.rolling(LONG_MA_PERIOD).mean()
    bias = (close - ma15) / ma15 * 100.0

    recent_bias = bias.tail(LOOKBACK_DAYS)
    if recent_bias.isna().all():
        return None

    if BIAS_DIRECTION == "up":
        hit = recent_bias.max() >= BIAS_THRESHOLD
        trigger_val = recent_bias.max()
    elif BIAS_DIRECTION == "down":
        hit = recent_bias.min() <= -BIAS_THRESHOLD
        trigger_val = recent_bias.min()
    else:
        hit_up = recent_bias.max() >= BIAS_THRESHOLD
        hit_down = recent_bias.min() <= -BIAS_THRESHOLD
        hit = hit_up or hit_down
        trigger_val = recent_bias.max() if abs(recent_bias.max()) >= abs(recent_bias.min()) else recent_bias.min()

    if not hit:
        return None

    latest_close = close.iloc[-1]
    latest_ma87 = ma87.iloc[-1]
    if pd.isna(latest_ma87) or latest_close <= latest_ma87:
        return None

    trigger_date = recent_bias.idxmax() if trigger_val > 0 else recent_bias.idxmin()

    return {
        "ticker": ticker,
        "name": name,
        "close": round(float(latest_close), 2),
        "ma87": round(float(latest_ma87), 2),
        "bias_pct": round(float(trigger_val), 2),
        "bias_date": trigger_date.strftime("%Y-%m-%d"),
        "as_of": close.index[-1].strftime("%Y-%m-%d"),
    }


def scan_universe(universe: list[dict], progress: bool = True) -> list[dict]:
    results = []
    total = len(universe)
    for i, row in enumerate(universe, 1):
        if progress and i % 50 == 0:
            print(f"進度 {i}/{total}")
        try:
            hit = evaluate(row["ticker"], row["name"])
            if hit:
                hit["market"] = row["market"]
                results.append(hit)
        except Exception as e:
            print(f"[warn] {row['ticker']} 失敗: {e}")
        time.sleep(REQUEST_SLEEP)
    results.sort(key=lambda r: abs(r["bias_pct"]), reverse=True)
    return results
