"""Audit a business workflow contract and render its skill or handoff."""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


VAGUE = {
    "協助", "協助處理", "幫我", "幫忙", "幫我處理", "優化", "處理", "處理資料",
    "必要時", "視情況處理", "適當處理", "執行任務", "任何任務", "任何需求", "所有業務", "任何工作",
    "自動處理", "重試", "無限重試", "幫我優化", "help", "help me", "as needed", "do anything",
    "handle it", "process data", "optimize", "retry",
}
CASES = {"normal": "正常執行", "outside_scope": "超出範圍", "failure": "失敗處理"}


def valid_text(value):
    return isinstance(value, str) and bool(value.strip())


def normalized(value):
    text = unicodedata.normalize("NFKC", value).casefold()
    return "".join(c for c in text if c.isalnum())


def check_contract(data):
    issues = []

    def issue(code, path, message):
        issues.append({"code": code, "path": path, "message": message})

    def obj(value, path):
        if not isinstance(value, dict):
            issue("FORMAT", path, "需要 JSON 物件。")
            return {}
        return value

    def phrase(value, path):
        if not valid_text(value) or not normalized(value):
            issue("TEXT", path, "請填入具體文字。")
            return False
        return True

    def names(value, path, identifiers=False):
        if not isinstance(value, list) or not value:
            issue("LIST", path, "需要至少一筆項目。")
            return []
        result = []
        seen = set()
        for i, name in enumerate(value):
            loc = f"{path}[{i}]"
            if not phrase(name, loc):
                continue
            if identifiers and not re.fullmatch(r"[a-z][a-z0-9_-]*", name):
                issue("IDENTIFIER", loc, "欄位與動作代碼請使用小寫英文、數字、連字號或底線。")
            key = name if identifiers else normalized(name)
            if key in seen:
                issue("DUPLICATE", loc, "清單項目重複。")
            seen.add(key)
            result.append(name)
        return result

    def fields(key):
        table = obj(data.get(key), key)
        if not table:
            issue("FIELDS", key, "需要定義欄位、格式及用途。")
        for field, definition in table.items():
            if not re.fullmatch(r"[a-z][a-z0-9_-]*", field):
                issue("IDENTIFIER", f"{key}.{field}", "欄位代碼無效。")
            phrase(definition, f"{key}.{field}")
        return set(table)

    data = obj(data, "$")
    if not isinstance(data.get("name"), str) or not re.fullmatch(
        r"(?=.{1,64}$)[a-z][a-z0-9]*(?:-[a-z0-9]+)*", data["name"]
    ):
        issue("NAME", "name", "使用 1～64 個小寫英數字與連字號命名。")
    phrase(data.get("title"), "title")
    activation = obj(data.get("activation"), "activation")
    include = names(activation.get("include"), "activation.include")
    exclude = names(activation.get("exclude"), "activation.exclude")
    ambiguous = {normalized(s) for s in VAGUE}
    for path, items in (("include", include), ("exclude", exclude)):
        for i, text in enumerate(items):
            key = normalized(text)
            if len(key) < 3 or key in ambiguous:
                issue("VAGUE_TRIGGER", f"activation.{path}[{i}]", "加上可辨認的業務動作、資料或交付物。")
    if {normalized(p) for p in include} & {normalized(p) for p in exclude}:
        issue("TRIGGER_CONFLICT", "activation", "相同條件同時要求啟動與排除。")
    if len(description(include, exclude)) > 1024:
        issue("DESCRIPTION", "activation", "請精簡啟動及排除條件，合計不超過 1,024 字元。")

    inputs, outputs = fields("inputs"), fields("outputs")
    allowed = set(names(data.get("allow"), "allow", identifiers=True))
    denied = set(names(data.get("deny"), "deny", identifiers=True))
    if allowed & denied:
        issue("RULE_CONFLICT", "allow/deny", "動作同時出現在允許與禁止清單。")
    available = set(inputs)
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        issue("STEPS", "steps", "需要至少一個可檢查的步驟。")
        steps = []
    produced = set()
    for i, raw in enumerate(steps):
        path = f"steps[{i}]"
        step = obj(raw, path)
        action = step.get("action")
        if not isinstance(action, str) or action not in allowed or action in denied:
            issue("UNAUTHORIZED_STEP", path + ".action", "步驟超過本次允許範圍。")
        reads = set(names(step.get("read"), path + ".read", identifiers=True))
        missing = sorted(reads - available)
        if missing:
            issue("MISSING_SOURCE", path + ".read", "尚未取得 " + "、".join(missing))
        writes = set(names(step.get("write"), path + ".write", identifiers=True))
        if writes & available:
            issue("OVERWRITE", path + ".write", "新產物需使用獨立代碼，讓接手者能追回原始輸入。")
        available.update(writes)
        produced.update(writes)
        instructions = step.get("instruction")
        if phrase(instructions, path + ".instruction") and normalized(instructions) in ambiguous:
            issue("FRAGILE_STEP", path + ".instruction", "步驟未說明實際作法。")
        failure = step.get("failure")
        if not isinstance(failure, dict) or not all(valid_text(failure.get(k)) for k in ("when", "then")):
            issue("FAILURE_HANDLING", path + ".failure", "填入可識別的失敗條件與處置。")
        else:
            response = normalized(failure["then"])
            if response in ambiguous:
                issue("FAILURE_HANDLING", path + ".failure.then", "需寫出可執行的處置與停止條件。")
            retry_forever = r"(?:無限|不停|不斷|持續)重試|重試直(?:到|至)成功|retry(?:untilsuccess|forever)"
            instructions_only = re.sub(r"(?:禁止|不得|不可|不要|切勿|避免)(?:" + retry_forever + ")", "", response)
            if re.search(retry_forever, instructions_only):
                issue("UNBOUNDED_RETRY", path + ".failure.then", "請移除無限重試指令，訂出次數與停止條件。")
            elif "retry" in failure or re.match(r"(?:請)?(?:重新嘗試|重試|retry)", response):
                retry = failure.get("retry")
                if (not isinstance(retry, dict) or type(retry.get("limit")) is not int
                        or retry["limit"] < 1 or not all(valid_text(retry.get(k)) for k in ("repeat_safe", "exhausted"))):
                    issue("UNBOUNDED_RETRY", path + ".failure.retry", "重試需正整數次數、可安全重複的理由及用盡後的處置。")
    if outputs - produced:
        issue("MISSING_OUTPUT", "outputs", "沒有步驟產出 " + "、".join(sorted(outputs - produced)))
    cases = obj(data.get("cases"), "cases")
    for kind in CASES:
        case = cases.get(kind)
        if not isinstance(case, dict) or not all(valid_text(case.get(k)) for k in ("input", "expected")):
            issue("ACCEPTANCE_CASE", "cases." + kind, "此案例需要輸入及可觀察的預期結果。")
    phrase(data.get("handoff"), "handoff")
    return issues


def description(include, exclude):
    return "適用於" + "、".join(include) + "。排除" + "、".join(exclude) + "。"


def render_skill(data):
    activation = data["activation"]
    trigger = description(activation["include"], activation["exclude"])
    lines = ["---", "name: " + data["name"], "description: " + json.dumps(trigger, ensure_ascii=False),
             "---", "", "# " + data["title"], "", "## 任務邊界", "",
             "只執行下列已授權的動作。", "", "- 允許：" + "、".join(data["allow"]),
             "- 禁止：" + "、".join(data["deny"])]
    for key, title in (("inputs", "輸入格式"), ("outputs", "輸出格式")):
        lines.extend(["", "## " + title, ""])
        lines.extend(f"- `{name}`　{detail}" for name, detail in data[key].items())
    lines.extend(["", "## 執行與失敗處理"])
    for i, step in enumerate(data["steps"], 1):
        lines.extend(["", f"### {i}. {step['action']}", "",
                      f"使用 {', '.join(step['read'])}，產出 {', '.join(step['write'])}。",
                      "", step["instruction"], "",
                      f"遇到「{step['failure']['when']}」時，{step['failure']['then']}"])
        if "retry" in step["failure"]:
            retry = step["failure"]["retry"]
            lines.append(f"至多重試 {retry['limit']} 次。安全重跑的依據：{retry['repeat_safe']}。次數用盡後：{retry['exhausted']}")
    lines.extend(["", "## 交付", "", data["handoff"], ""])
    return "\n".join(lines)


def render_handoff(data):
    lines = ["# " + data["title"] + "｜接手驗收", "", data["handoff"], "",
             "使用契約中的輸入在指定平台逐案執行，將實際產物與預期比對。", "",
             "執行環境、版本與日期：待填。"]
    for kind, label in CASES.items():
        case = data["cases"][kind]
        lines.extend(["", "## " + label, "", "- 案例輸入：" + case["input"],
                      "- 預期：" + case["expected"], "- 實際輸出與紀錄：待執行",
                      "- 判定、差異與接手人：待填"])
    return "\n".join(lines) + "\n"


def unique_keys(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("重複的 JSON 欄位：" + key)
        data[key] = value
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--emit", choices=("skill", "handoff"))
    mode.add_argument("--verify", type=Path, metavar="SKILL.md")
    args = parser.parse_args()
    try:
        data = json.loads(args.contract.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_keys)
        issues = check_contract(data)
        if not issues and args.verify and args.verify.read_text(encoding="utf-8") != render_skill(data):
            issues.append({"code": "SPEC_DRIFT", "path": str(args.verify), "message": "技能文字與契約編譯結果不同。"})
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    report = {"status": "invalid" if issues else "valid", "issues": issues}
    if issues or not args.emit:
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr if args.emit else sys.stdout)
    else:
        sys.stdout.write(render_skill(data) if args.emit == "skill" else render_handoff(data))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
