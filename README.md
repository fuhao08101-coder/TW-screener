# TW Screener — 台股15MA乖離掃描

近 N 個交易日內觸及「15MA乖離 20%」、且還原日K收盤價站上 SMA87 的股票篩選器。
每天自動跑,結果用手機瀏覽器看,免架站、免費。

## 部署步驟(約10分鐘,只需做一次)

1. **建立 GitHub 帳號**(免費):https://github.com/signup

2. **建立新 repository**
   - 右上角 `+` → `New repository`
   - 命名例如 `tw-screener`,設為 **Public**(GitHub Pages免費版需要Public)
   - 建立完成後,把這個資料夾裡所有檔案上傳上去
     (網頁上可以直接拖曳上傳,或用 `git push`,不會用 git 的話用網頁拖曳最簡單)

3. **開啟 GitHub Pages**
   - repo 內 `Settings` → `Pages`
   - Source 選 `Deploy from a branch`,Branch 選 `main`,資料夾選 `/docs`
   - 存檔後,幾分鐘內會產生一個網址,例如
     `https://你的帳號.github.io/tw-screener/`
   - **這個網址就是你手機上要打開看結果的頁面**,可以加到手機主畫面變成「App圖示」

4. **啟用每日自動掃描**
   - repo 內 `Actions` 分頁,允許 workflow 執行(第一次要按確認)
   - 想立刻測試效果:`Actions` → `Daily TW Stock Screener` → `Run workflow`
     跑完(約幾分鐘~十幾分鐘,視股票數量)後,回到步驟3的網址重新整理就會看到結果
   - 之後每個台股交易日下午會自動跑一次,不用手動操作

## 關於「手機版 Python」的問題

**不需要**。整個設計是「雲端跑程式,手機只負責看網頁結果」——
- 真正執行 Python 掃描的是 GitHub 的伺服器(GitHub Actions),不是你的手機
- 你的手機只是用瀏覽器打開一個網頁看JSON整理後的結果,跟看任何網站一樣
- 這樣的好處:手機不用裝 Python、不用一直開著、不耗電、未來要做「推播通知」或「會員收費」都好擴充

如果你未來想要「即時盤中」而不是「收盤後」的版本,那才需要考慮更複雜的架構(常駐伺服器 + WebSocket),但那個等MVP驗證有需求後再做。

## 條件參數怎麼調

打開 `src/screener.py` 最上面幾行:

```python
LOOKBACK_DAYS = 10        # 近幾個交易日內
BIAS_MA_PERIOD = 15       # 乖離用的均線天數
BIAS_THRESHOLD = 20.0     # 乖離門檻(%)
LONG_MA_PERIOD = 87       # 長期均線天數
BIAS_DIRECTION = "both"   # "up"只抓急漲後拉回 / "down"只抓急跌反彈 / "both"兩者都要
```

改完後 commit 上去,下次自動跑就會用新條件。

## 資料準確度的重要提醒

目前用的是免費資料源(yfinance + 交易所公開清單),還原權息的方式是自動調整(`auto_adjust=True`),
跟券商軟體(如圖片中那套)的還原邏輯可能有些微差異,盤中資料也可能有延遲。
如果之後要做成正式收費產品,建議升級成永豐金 Shioaji 或富果 Fugle 的正式API,資料品質與即時性會好很多。

## 免責聲明

僅供程式研究與個人參考,非投資建議,請自行核對數據正確性。
