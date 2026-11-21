# 智研代理任務清單

每次工作回報請寫明輸入版本、交付物、執行過的驗收與尚待補齊的條件。以下指令均從本專案根目錄在 Linux 或 WSL 執行。客戶原始資料、工作輸出與實際影片留在案件的工作目錄。

| 任務 | 啟動條件 | 交付與完成判準 |
| --- | --- | --- |
| 市場定價 | 新增服務、調整範圍或重新評估定價 | 取得公開原始價目、權益與加購條款，按同一計價單位比較，列出原始及排除離群值後的結果。 |
| 網站設計與發布 | 服務、表單、版面或互動修改 | 對照桌機與手機、鍵盤與觸控及實際載入量。正式網域的內容必須與發布提交相符。 |
| 商務技能交付 | 業主能指出一個重複工作和可判定的結果 | 產出可載入的技能檔、輸入／輸出範例、故障行為及交接說明。驗收包含應啟動、不應啟動、資料缺件和規則衝突。 |
| Hermes 短影音 | 有題材、來源、成片規格及可使用的視聽素材 | 六階段以 JSON（資料交換格式）傳遞產物。配音與影像時長可對應，底板、遮罩與合成檢查可重現，失敗可以定位並續跑。 |
| 官網服務與工程數據 | 對外服務異動，或 GitHub 來源版本更新 | 公開交付項目、聯絡入口和有來源的統計。同步後比對正式頁面與數據，不把規劃中的功能列為實測成果。 |

## 一、市場定價

採集同業官網或賣家自己刊登的方案。每家在每類只計一筆，取能滿足該範圍的最低公開價。將幣別、計價單位、功能、教學、修正、文件或對話額度、主機、模型與維護費一併留存。一次收取建置費不能據以推定程式碼或著作權歸屬。按件、按月、按量與組合收費分列。

```bash
mkdir -p /tmp/zhiyan-pricing
python3 agents/pricing/collect.py --output /tmp/zhiyan-pricing/quotes.json
```

核對報價原頁、樣本數、中位數、原始平均與 1.5 倍四分位距的排除項。遇到來源無法讀取、單位不明或同頁多層方案無法分辨時，交接給人工覆核。研究結果用於討論定位，客戶售價依核定方案發布。[採集器與計價口徑](pricing/)

## 二、網站設計與發布

從一項訪客任務開始，例如從寫作服務帶入詢問表單，或核對作品數字的來源。Emil Kowalski 的作品目錄用名稱和一行說明讓訪客決定要看哪一件；Studio Feixen 用分類與文字連結讓人掃讀大量作品。智研服務列保留單一詢問動作，以中文字級、留白和細分隔線呈現層次。前端沿用本機字型、原生控制項與依內容分版的檔案。[Emil Kowalski](https://emilkowal.ski/) · [Studio Feixen](https://www.studiofeixen.ch/)

```bash
git remote -v
python3 scripts/release.py build
python3 scripts/release.py check
node --check src/app.js
```

至少覆核 320、390、768 及 1280 像素、明暗色、鍵盤焦點、主要點擊區與手機選單。修改聯絡或服務時要實際產生草稿，檢查收件人與預選項目。合併後執行 `python3 scripts/release.py verify-live` 比對正常首頁網址及其本機資源；快取尚未換版時先查部署與檔案指紋。[發布說明](../README.md)

## 三、把商業需求做成可交接的技能

輸入一項有範圍的工作、預期產物、缺件時的動作及可否對外傳送等限制。審查後分別產出執行用技能檔及給接手人的操作說明。

```bash
python3 agents/skill-delivery/scripts/review.py agents/skill-delivery/references/interview.json
python3 agents/skill-delivery/scripts/review.py agents/skill-delivery/references/interview.json --emit skill
python3 agents/skill-delivery/scripts/review.py agents/skill-delivery/references/interview.json --emit handoff
```

以同一份案例檢查含糊的啟動條件、相互衝突的動作、缺少必要輸入的步驟及失敗後的交接。靜態檢查後，再用正常需求、相近但應排除的需求與資料缺失各跑一次。模型的實際回覆須獨立驗收。[技能入口](skill-delivery/SKILL.md)

## 四、Hermes 短影音六階段

| 階段 | 輸入與應保留的證據 |
| --- | --- |
| 題材蒐集 | 題目、查詢範圍與可用來源。保存標題、網址及與腳本相關的材料，可使用 Tavily 或 Perplexity。 |
| 腳本創作 | 從已選來源撰寫旁白與分鏡，讓後續人員能回查出處。 |
| 視覺生成 | 底板、構圖、前景與可使用的素材。固定背景專案只採一張對齊尺寸的底板。 |
| 圖生影／動態 | 即時生成、已授權的動態素材，或用 LivePortrait 驅動前景。保存此階段的影格或影片。 |
| 語音合成 | 以已定稿旁白產生音軌或接入獲授權的錄音。核對語言、讀音、時長。 |
| FFmpeg 剪輯 | 綠幕色鍵或對齊遮罩把前景回貼到底板，完成合成、音畫封裝與逐幀驗收。 |

```bash
python3 agents/short-video/run.py agents/short-video/job.example.json /tmp/zhiyan-video-demo
```

範例使用本機測試素材，避免重複呼叫付費服務。商用任務要另外核對指定供應商、素材與授權、台灣華語旁白、嘴型及交付編碼。對齊後逐幀檢查無損母帶的遮罩外像素，另量有損成片的色差與閃爍；換素材後重新驗收。[短影音實作與接手說明](short-video/) · [公開 CineAgent 入口](https://github.com/Lucien-1127/CineAgent)

## 五、對外服務與 GitHub 同步

提示詞工廠交付可重用的指令、規則審查與壓縮前後驗收。寫作指令服務依目的快速編譯，或以訪談釐清讀者、語氣和文類，再交付可重用的寫作指令。網站提供洽詢示範入口。公開說明只列與交付有關的技術，例如 Docker（容器）、Linux／WSL、REST API（服務介面）。

```bash
python3 scripts/sync_evidence.py refresh
python3 scripts/sync_evidence.py check
# 合併並發布到正式網域後執行
python3 scripts/release.py verify-live
```

每日台灣時間 **07:17** 排程核對 GitHub 預設分支，也可在工作流程頁面手動啟動。法條數取法律專案每部法規最新的收錄版本，排除舊版本、空白與刪除條次；測試與情境分別取提示詞工廠的測試方法與唯一情境編號。來源版本與數字一同更新。有來源錯誤時保留前次已驗證值；有更新時以一般提交發布，並從正式網域逐檔核驗。[來源快照](../data/project-evidence.json) · [定時同步紀錄](https://github.com/Lucien-1127/zhiyan-studio/actions/workflows/sync-evidence.yml)
