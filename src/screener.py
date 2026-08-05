"""
核心篩選邏輯:
  條件1:最近 N 個交易日內,曾出現「收盤價相對15MA乖離率 >= BIAS_THRESHOLD%」
  條件2:最新一根還原日K收盤價 > SMA87
  條件3(剃除用):最近 MA87_BREACH_LOOKBACK 個還原日內，不得曾經跌破87MA
               (只要有任一天收盤 < 87MA，整檔剃除)

還原日K:使用 yfinance auto_adjust=True,會依除權息回推調整 OHLC。
"""
from __future__ import annotations
import time
import pandas as pd
import yfinance as yf

# ------- 可調參數 -------
LOOKBACK_DAYS = 10        # 「10個交易日內」(用於15MA乖離判斷)
BIAS_MA_PERIOD = 15       # 15MA
BIAS_THRESHOLD = 20.0     # 乖離 20%
LONG_MA_PERIOD = 87       # SMA87
BIAS_DIRECTION = "up"     # "up"=只抓正乖離(急漲) / "down"=只抓負乖離(急跌) / "both"=兩者都抓

MA87_BREACH_LOOKBACK = 14  # 條件3：檢查最近幾個交易日內是否曾跌破87MA(依您這次訊息設為14)

# 已經拿掉「兩年新高」濾網，不再需要抓5年資料，改回1年即可，抓取速度會比之前快
HISTORY_PERIOD = "1y"
REQUEST_SLEEP = 0.5       # 每檔股票間的延遲,避免被限流
# ------------------------

# 需要的最少歷史交易日數：87MA需要87天 + 檢查視窗 + 緩衝
MIN_REQUIRED_ROWS = LONG_MA_PERIOD + MA87_BREACH_LOOKBACK + 10


def fetch_history(ticker: str) -> pd.DataFrame | None:
    try:
        df = yf.Ticker(ticker).history(period=HISTORY_PERIOD, auto_adjust=True)
        if df is None or df.empty or len(df) < MIN_REQUIRED_ROWS:
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

    # ---- 條件1：近 LOOKBACK_DAYS 日內曾出現乖離 ----
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

    # ---- 條件2：最新收盤 > 87MA ----
    latest_close = close.iloc[-1]
    latest_ma87 = ma87.iloc[-1]
    if pd.isna(latest_ma87) or latest_close <= latest_ma87:
        return None

    # ---- 條件3(剃除)：近 MA87_BREACH_LOOKBACK 日內不得曾跌破87MA ----
    recent_close_87 = close.tail(MA87_BREACH_LOOKBACK)
    recent_ma87_check = ma87.tail(MA87_BREACH_LOOKBACK)
    if recent_ma87_check.isna().any():
        return None  # 87MA 資料不足以判斷，保守剃除
    if (recent_close_87 < recent_ma87_check).any():
        return None  # 近期曾跌破87MA，剃除

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
