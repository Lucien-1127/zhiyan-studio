# Hermes 主播短影音

這個入口依序執行題材研究、腳本、視覺、動態、配音、剪輯。每次處理一段固定鏡位的主播短片，完成時交付有聲 MP4、無損母帶與逐幀背景量測。用設定檔選供應商，工作目錄保存每階段的 JSON 與檔案指紋。

## 執行與續跑

在 Linux 或 WSL 的本目錄執行。使用含 NumPy、Pillow 的 Python 3.11 以上環境，以及附 FFV1、libx264、AAC 的 FFmpeg、ffprobe。範例另用 FFmpeg 的 Flite 濾鏡合成一句英文測試語音，全程在本機執行。

```bash
python3 run.py job.example.json /tmp/studio-short-demo
python3 check.py
```

正式任務由 Hermes 寫入一份 job JSON，使用獨立的工作目錄。先填題材、供應商、素材路徑、預期秒數與每秒格數，並與客戶確認可接受的成品背景誤差。輸入檔路徑可相對於 job 檔。服務憑證由執行環境提供。暫存素材、媒體連結與客戶聲音請放在公開網站儲存庫以外。

```bash
python3 run.py job.json /tmp/studio-short-client --stop-after script
python3 run.py job.json /tmp/studio-short-client
```

### 六階段交接

| 階段 | 可選執行器 | 交付及通過條件 |
| --- | --- | --- |
| 題材 | `sources` 讀已核對的來源包，或 `tavily`、`perplexity` 搜尋題材 | `research.json` 含來源編號、HTTPS 網址、標題、摘要、擷取時間。零筆有效來源會中止。 |
| 腳本 | `extract` 用已確認的旁白或首筆來源摘要製作單鏡腳本；`cineagent` 根據題材與已取得的來源生成腳本 | `script.json` 含旁白、所採用的來源編號、視覺提示及動作提示；來源編號須能回查。 |
| 視覺 | `provided` 載入授權主播素材；`cineagent` 呼叫既有影像模組；`fixture` 產生測試圖形 | `visual.json` 對應 `plate.png`、`mask.png`、`presenter.png`。底板和遮罩須對齊，遮罩須同時含保護區與可動區。 |
| 動態 | `provided` 載入前景影片；`cineagent` 以先前生成的圖送出圖生影；`liveportrait` 以主播原圖和驅動影片執行已安裝模型；`fixture` 產生逐格運動 | `motion.json` 與 `motion.mkv`。CineAgent 取得工作編號後寫入 `video-job.json`，恢復時查詢既有工作。 |
| 配音 | `piper` 以指定本機語音模型合成；`recording` 讀取已授權錄音；`fixture-flite` 合成測試英文 | `voice.json` 與 `voice.wav`。剪輯時核對有音軌及旁白時長。 |
| 剪輯 | `ffmpeg` 固定底板合成、加上配音、編碼及驗收 | `master.mkv`、`short.mp4` 及 `edit.json`。逐格量測、容差、影格數與音軌都通過後，此階段才記為完成。 |

結構化資料採 UTF-8。每階段 `state.json` 的狀態為 `running`、`done` 或 `blocked`；尚未開始的階段不會出現。已完成的輸出須與記錄的 SHA-256 相符才可續用。若素材或 job 改動，另開目錄。中斷或供應商失敗時，先核對工作編號與可能的費用，再使用 `--retry 階段名稱`。每個目錄同時只允許一次執行。

## 正式設定

- 將 `kind` 設為 `production`。正式題材可選 `research: tavily` 與 `TAVILY_API_KEY`，或 `research: perplexity` 與 `PERPLEXITY_API_KEY`。已有查證過的資料時，使用 `research: sources` 並填入 `sources`。兩個查詢入口都是業者官方搜尋 API。[Tavily](https://docs.tavily.com/documentation/api-reference/endpoint/search) · [Perplexity](https://docs.perplexity.ai/api-reference/search-post)
- 使用 CineAgent 時，`CINEAGENT_DIR` 指向已備妥相依套件的公開版本，另設定自己的 `AGNES_API_KEY`。入口重用 `AgnesAPI.chat`、影像提示、`generate_image`、`generate_video` 及 `poll_video`。圖生影可設定 5、10 或 15 秒。首次檢查可停於腳本階段。[Hermes 入口](https://github.com/Lucien-1127/hermes-skills/blob/fc0a8c57676bcd44cade54644403bcf69be151e9/cineagent-oneclick/cineagent-oneclick.md) · [CineAgent 實作](https://github.com/Lucien-1127/CineAgent/blob/5d5ea507208222c971aa8ccd2e524c3490c1be33/run_pipeline.py)
- 正式視覺設定 `files.plate`、`files.mask`。使用現有主播圖時填 `files.presenter`。綠幕前景配 `mode: chroma`，已錄影可填 `files.motion` 並選 `motion: provided`。預設前景與底圖同尺寸；綠幕需要等比縮放及補邊時，另設 `fit_motion: contain`，逐片確認位置。[FFmpeg 色鍵說明](https://ffmpeg.org/ffmpeg-filters.html#colorkey)
- LivePortrait 設 `motion: liveportrait`、`mode: mask`，提供 `files.driving` 與對齊原圖的靜態灰階遮罩。配好模型與授權素材後以 `LIVEPORTRAIT_DIR` 指向安裝目錄，必要時以 `LIVEPORTRAIT_PYTHON` 指定該環境 Python。程式呼叫一段影片的推論入口並讀回貼回原圖尺寸的成品。[LivePortrait 原始專案](https://github.com/KlingAIResearch/LivePortrait)
- 中文配音設定 `voice: piper`、`files.voice_model`，使用配有設定檔與授權的中文模型；可用 `PIPER_PYTHON` 指定環境。也可選 `voice: recording` 並填 `files.recording`。配音長於企劃鏡頭時會停在剪輯階段，保留已完成素材。[Piper 指令說明](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md)

## 背景驗收

遮罩為純黑的像素代表「固定底板」，白色代表可動區，灰色為羽化邊緣。綠幕模式先以 FFmpeg RGB 色鍵產生透明度，再乘上固定遮罩。LivePortrait 模式則將動態前景依同一靜態遮罩貼回底板，避免模型對原圖其他位置的修改滲入成品。

無損 FFV1 母帶逐格以 RGB 比對原始底板，純黑遮罩區要求每一通道差值為零。H.264 成品另外量測每格背景相對底板的平均絕對誤差，以及相鄰兩格背景的平均絕對差。兩項均取最差影格與 job 的 `delivery_limits` 比對，單位為 8 位元色階 0～255。範例門檻分別是 4 與 2。人物邊緣、髮絲與唇形仍須用實際獲授權素材檢視。

`check.py` 使用有意在遮罩外閃動的測試圖，同時測綠幕、遮罩、續跑、缺來源與產物變動。這組測試涵蓋從來源包到有聲 MP4 的本機交付。公開接頭的帳號額度、使用中的模型、真人主播及繁中聲音需在相應環境以真實素材驗收。
