"""
抓取台股上市(TWSE) + 上櫃(TPEx) 股票代號清單。
資料來源為交易所公開資料 API,免費、免申請。
"""
import requests

TWSE_LIST_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_LIST_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; tw-screener/1.0)"}


def get_twse_list() -> list[dict]:
    """上市公司清單,回傳 [{code, name, market}]"""
    r = requests.get(TWSE_LIST_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    out = []
    for row in data:
        code = row.get("公司代號")
        name = row.get("公司簡稱")
        if code and code.isdigit():
            out.append({"code": code, "name": name, "market": "TWSE"})
    return out


def get_tpex_list() -> list[dict]:
    """上櫃公司清單,回傳 [{code, name, market}]"""
    r = requests.get(TPEX_LIST_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    out = []
    for row in data:
        code = row.get("SecuritiesCompanyCode") or row.get("Code")
        name = row.get("CompanyName") or row.get("Name")
        if code and str(code).isdigit():
            out.append({"code": str(code), "name": name, "market": "TPEX"})
    return out


def get_universe(include_otc: bool = True) -> list[dict]:
    """
    取得完整股票清單。任一來源失敗不會讓整體掛掉,只會少那個市場的股票。
    yfinance 代號規則: 上市加 .TW, 上櫃加 .TWO
    """
    universe = []
    try:
        universe += get_twse_list()
    except Exception as e:
        print(f"[warn] 上市清單抓取失敗: {e}")

    if include_otc:
        try:
            universe += get_tpex_list()
        except Exception as e:
            print(f"[warn] 上櫃清單抓取失敗: {e}")

    for row in universe:
        suffix = ".TW" if row["market"] == "TWSE" else ".TWO"
        row["ticker"] = f"{row['code']}{suffix}"

    return universe


if __name__ == "__main__":
    u = get_universe()
    print(f"共取得 {len(u)} 檔股票")
    print(u[:5])
