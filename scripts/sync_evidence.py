"""Refresh publicly reproducible site metrics from two pinned Git trees."""

import argparse
import ast
from datetime import date
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = Path("data/project-evidence.json")
OWNER = "https://github.com/Lucien-1127"
LAW_REPO = "zhiyan-legal"
PROMPT_REPO = "prompt-factory"
LAW_DIR = "data/articles"
TEST_PATH = "scripts/test_validate_prompt_factory.py"
SCENARIO_PATH = "evals/behavior-cases.json"
BEGIN = "<!-- evidence:start -->"
END = "<!-- evidence:end -->"


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def decode(data):
    return json.loads(data, object_pairs_hook=unique_keys)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=90)


def checkout(temp, name, supplied=None):
    if supplied is None:
        supplied = Path(temp) / name
        subprocess.run(["git", "clone", "--quiet", "--depth=1", "--single-branch",
                        "--no-checkout", f"{OWNER}/{name}.git",
                        str(supplied)], check=True, timeout=150)
    origin = git(supplied, "remote", "get-url", "origin").decode().strip().removesuffix(".git")
    if origin not in (f"{OWNER}/{name}", f"git@github.com:Lucien-1127/{name}"):
        raise ValueError(f"unexpected upstream for {name}: {origin}")
    rev, day = git(supplied, "show", "-s", "--format=%H %cs", "HEAD").decode().strip().split()
    return supplied, {"revision": rev, "commit_date": day}


def count_articles(editions):
    if not isinstance(editions, dict):
        raise ValueError("law editions must be an object")
    dates = [k for k in editions if re.fullmatch(r"[0-9]{8}", k)]
    if not dates or set(editions).difference(dates, {"_oldver"}):
        raise ValueError("unrecognized law edition format")
    for stamp in dates:
        date.fromisoformat(f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}")
    articles = editions[max(dates)]
    if not isinstance(articles, dict) or not articles:
        raise ValueError("empty law edition")
    count = 0
    for number, text in articles.items():
        if not re.fullmatch(r"[1-9][0-9]*(?:-[0-9]+)*", number) or not isinstance(text, str):
            raise ValueError(f"invalid article record: {number}")
        text = text.strip()
        if text and not re.fullmatch(r"[（(]?\s*刪\s*除\s*[）)]?[。.]?", text):
            count += 1
    return count


def law_counts(root, revision):
    listing = git(root, "ls-tree", "-z", f"{revision}:{LAW_DIR}").decode()
    laws, articles = 0, 0
    for entry in listing.rstrip("\0").split("\0"):
        metadata, name = entry.split("\t", 1)
        if not name.endswith(".json"):
            continue
        if not re.fullmatch(r"[A-Z][0-9]{7}\.json", name) or not metadata.startswith("100644 blob "):
            raise ValueError(f"unexpected law file: {name}")
        articles += count_articles(decode(git(root, "show", f"{revision}:{LAW_DIR}/{name}")))
        laws += 1
    return {"laws": laws, "articles": articles}


def prompt_counts(test_source, cases):
    module = ast.parse(test_source)
    tests = set()
    for cls in module.body:
        if not isinstance(cls, ast.ClassDef):
            continue
        if not any(ast.unparse(base) in {"unittest.TestCase", "TestCase"} for base in cls.bases):
            continue
        for method in cls.body:
            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith("test_"):
                tests.add((cls.name, method.name))
    if not isinstance(cases, dict) or not isinstance(cases.get("cases"), list):
        raise ValueError("missing behavior scenarios")
    ids = set()
    for case in cases["cases"]:
        key = case.get("id") if isinstance(case, dict) else None
        if not isinstance(key, str) or not key.strip() or key in ids:
            raise ValueError("missing or duplicate behavior scenario ID")
        ids.add(key)
    return {"tests": len(tests), "scenarios": len(ids)}


def collect(args):
    with TemporaryDirectory() as temp:
        legal_root, legal = checkout(temp, LAW_REPO, args.legal_root)
        prompt_root, prompts = checkout(temp, PROMPT_REPO, args.prompt_root)
        legal.update(law_counts(legal_root, legal["revision"]))
        revision = prompts["revision"]
        prompts.update(prompt_counts(git(prompt_root, "show", f"{revision}:{TEST_PATH}"),
                                     decode(git(prompt_root, "show", f"{revision}:{SCENARIO_PATH}"))))
    return {"schema": 1, LAW_REPO: legal, PROMPT_REPO: prompts}


def validate(data):
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise ValueError("unexpected evidence schema")
    for name, counters in [(LAW_REPO, ("laws", "articles")), (PROMPT_REPO, ("tests", "scenarios"))]:
        source = data[name]
        if not re.fullmatch(r"[0-9a-f]{40}", source["revision"]):
            raise ValueError(f"invalid commit for {name}")
        date.fromisoformat(source["commit_date"])
        if any(type(source[key]) is not int or source[key] < 1 for key in counters):
            raise ValueError(f"empty or invalid count for {name}; keeping the last verified snapshot")


def render(data):
    validate(data)
    laws, prompts = data[LAW_REPO], data[PROMPT_REPO]
    law = f"{OWNER}/{LAW_REPO}/tree/{laws['revision']}/{LAW_DIR}"
    prompt = f"{OWNER}/{PROMPT_REPO}/blob/{prompts['revision']}"
    return f'''      <section class="project-evidence" aria-labelledby="evidence-title">
        <h3 id="evidence-title">公開工程數據</h3>
        <ul class="evidence-list">
          <li><strong>{laws['articles']:,} 條</strong><span>法律研究資料夾收錄 {laws['laws']} 部法規，各取最新收錄版本，排除空白與標記刪除的條次。</span><a href="{law}">核對法規快照</a></li>
          <li><strong>{prompts['tests']:,} 項</strong><span>提示詞工廠驗證程式中定義的自動回歸測試方法。</span><a href="{prompt}/{TEST_PATH}">查看測試定義</a></li>
          <li><strong>{prompts['scenarios']:,} 組</strong><span>提示詞工廠列有獨立編號的行為驗收情境。</span><a href="{prompt}/{SCENARIO_PATH}">查看情境與預期結果</a></li>
        </ul>
        <p>來源版本日期：法律 {laws['commit_date']}、提示詞 {prompts['commit_date']}。<a href="./{SNAPSHOT_PATH.as_posix()}">下載數據</a> · <a href="{OWNER}/zhiyan-studio/actions/workflows/sync-evidence.yml">查看同步紀錄</a></p>
      </section>'''


def replace_block(page, block):
    if page.count(BEGIN) != 1 or page.count(END) != 1:
        raise ValueError("index.html must have exactly one pair of evidence markers")
    before, rest = page.split(BEGIN)
    _, after = rest.split(END)
    return f"{before}{BEGIN}\n{block}\n{END}{after}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("refresh", "check"))
    parser.add_argument("--legal-root", type=Path, help="existing public zhiyan-legal checkout")
    parser.add_argument("--prompt-root", type=Path, help="existing public prompt-factory checkout")
    args = parser.parse_args()
    snapshot = ROOT / SNAPSHOT_PATH
    index = ROOT / "index.html"
    page = index.read_text(encoding="utf-8")
    data = collect(args) if args.action == "refresh" else decode(snapshot.read_bytes())
    new_page = replace_block(page, render(data))
    if args.action == "check":
        if page != new_page:
            raise ValueError("HTML differs from the verified snapshot; refresh the site evidence")
    else:
        snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        index.write_text(new_page, encoding="utf-8")
    print(f"Verified {data[LAW_REPO]['articles']:,} articles, {data[PROMPT_REPO]['tests']} test methods, "
          f"{data[PROMPT_REPO]['scenarios']} behavior scenarios.")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, TypeError, ValueError, SyntaxError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from error
