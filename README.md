# 智研工作室

客製 AI 工作流與知識庫服務網站。GitHub Pages 從 `main` 分支的根目錄發布至 [lucien126.com](https://lucien126.com/)。

市場報價、前端、技能交付、短影音及公開數據各有可重跑的入口。[智研代理任務清單](agents/README.md)

## 修改與驗收

在 Linux 或 WSL 的專案根目錄執行以下指令。內容編輯在 `index.html`，樣式和互動編輯在 `src/`。

```bash
python3 scripts/release.py build
python3 scripts/release.py check
node --check src/app.js
```

將 HTML 及產生的 `assets/site-*` 一併提交。變更內容會產生新檔名。根目錄的舊 CSS、JavaScript、既有的雜湊檔和社群分享圖請保留，讓已開啟的舊頁面仍能讀到它原本搭配的資源。

合併前以手機和桌面檢查頁首底稿、導覽、深淺模式、方案帶入與郵件草稿。正式部署成功後，在對應提交再次檢查正式首頁及其本地資源。

```bash
python3 scripts/release.py verify-live
```

這個檢查透過正式網址逐一比對檔案內容及回報快取標頭。快取尚未更新時會失敗，可於首頁快取期過後重試。如需回復版本，從目標合併記錄建立還原提交並循同一流程發布。

## 公開工程數據

每日台灣時間 07:17 核對兩個公開來源。從 GitHub 指定版本的資料檔計數，將來源提交與日期寫入 `data/project-evidence.json`，並同步至首頁。頁面直接顯示數據，訪客可點每項旁的來源連結核對。來源缺漏、格式改變或解析失敗會使該次同步停止並保留上一份快照。

在 Linux 或 WSL 的專案根目錄可重新收集，或只比對已提交的快照與頁面。

```bash
python3 scripts/sync_evidence.py refresh
python3 scripts/sync_evidence.py check
```

如果部署停留在舊版，可從同一工作流程的 `Run workflow`（手動執行）重驗並要求 Pages 重建。[同步與發布紀錄](https://github.com/Lucien-1127/zhiyan-studio/actions/workflows/sync-evidence.yml)
