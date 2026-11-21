---
name: zhiyan-skill-delivery
description: 客戶或智研承辦人要求把特定業務流程（如訪談整理、案件交接或報價彙整）製成可重用的代理技能，並需要 SKILL.md、規則審查、驗收案例與接手文件時使用。單次代寫、實際寄送、一般提示詞優化或審查任意既有技能，交回各自的流程。
---

# 商務代理技能交接

取得一個可公開或已去識別化的工作範例，問清楚誰觸發、讀什麼、做完交給誰，以及接手者怎麼知道結果正確。沿用需求中已有的答案。缺少會改變交付範圍或授權的資料時，列出已確定事項並提出最少的補件問題。

## 將需求寫成契約

以 [references/interview.json](references/interview.json) 為完整可執行範例，另存個案的 `contract.json`。使用一案一個技能名稱。用流程作者自己的業務語言填寫以下欄位。

- `name` 與 `title` 是技能識別及人可閱讀的標題。`activation.include` 要同時說明工作動作與對象。`activation.exclude` 描述容易混淆的相鄰需求。
- `inputs`、`outputs` 以欄位代碼對應「格式及用途」，列出接手方需要的欄位、單位和缺值表示法。
- `allow`、`deny` 以動作代碼記錄這次委託的邊界。沒有列在允許清單的動作不執行。對外傳送、發布、付款等行為只有明確受委託才納入。
- `steps` 依資料流排序。每步的 `read` 僅可引用輸入或已產生的資料，`write` 命名它新產生的結果。`instruction` 說明如何完成該步。`failure.when` 指出可辨認的失敗，`failure.then` 寫出保存哪些既有結果、如何求援或停止。有重試時，在 `failure.retry` 填入 `limit`（正整數）、`repeat_safe`（為何可安全重跑）及 `exhausted`（用盡次數的處置）。
- `cases` 放入真實工作形狀的正常、排除與故障三類案例，分別標示 `normal`、`outside_scope`、`failure`。每案提供要交給代理的文字及可觀察的預期結果。`handoff` 寫明接手角色與必查項目。

先自己核對一次金額、日期、欄位與資料授權是否能從需求追溯。當契約整理自既有自由文字技能，將原文與契約逐條比較，列出仍需判斷的語意衝突。

## 審查、編譯與交接

在 Linux 或 WSL，以本技能目錄為工作目錄執行。Python 3.9 以上即可使用，腳本只讀取指定的 JSON 或 Markdown，產物寫至標準輸出。

以下指令使用隨附範例。執行個案時，將 `contract` 設為該案的契約路徑。

```bash
contract=references/interview.json
delivery_dir=$(mktemp -d)
python3 scripts/review.py "$contract" &&
  cp "$contract" "$delivery_dir/contract.json" &&
  python3 scripts/review.py "$contract" --emit skill > "$delivery_dir/SKILL.md" &&
  python3 scripts/review.py "$contract" --emit handoff > "$delivery_dir/HANDOFF.md" &&
  python3 scripts/review.py "$contract" --verify "$delivery_dir/SKILL.md" > "$delivery_dir/review.json" &&
  printf '%s\n' "$delivery_dir"
```

審查回傳問題代碼和欄位路徑。修正契約後重新產出兩份文件。將輸出目錄內的檔案交給接手者。使用 `python3 scripts/test_review.py` 重跑本工具的故障注入測試。

將三種案例在指定目標代理逐一執行。記下環境、實際輸出、預期差異與通過／失敗。[references/interview-handoff.md](references/interview-handoff.md) 有一份已執行的接手紀錄。未取得使用環境時，在交接單保留「待執行」。檢查器可驗證明示允許／禁止衝突、常見空泛觸發字、無來源步驟、缺少失敗出口及規格檔不一致。隱含矛盾、事實與模型實際行為須以人工複核與案例執行判斷。
