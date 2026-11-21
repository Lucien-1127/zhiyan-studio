"""Recheck named public Taiwanese offers and compute like-for-like project benchmarks."""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from statistics import mean, median, quantiles
import sys
from tempfile import NamedTemporaryFile
from time import monotonic, sleep
import unicodedata
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from sources import FLOW, KB, OFFERS, UNIT_SETUP


BOT = "ZhiyanPriceResearch"
USER_AGENT = BOT + "/1.0 (+https://lucien126.com/)"
LIMIT = 4 * 1024 * 1024
NUMBER = r"(?P<twd>(?:[1-9]\d{0,2}(?:,\d{3})+|[1-9]\d*))(?![\d,.])"
PERIODIC = re.compile(r"(?:須|必須|強制)(?:另行|另外)?(?:搭配|加購|簽訂|支付)[^\n。;]{0,12}(?:月費|月租|維護合約|年約)")
# These are excerpts, not a claim that a fee or service is included.
TERM_HINTS = {
    "features": r"交付|檢索式回答|測試題庫|操作文件|建置|流程盤點|操作說明|核心功能|對話介面",
    "support": r"保固|免費修正|維運|維護|技術支援|轉真人",
    "extra": r"另計|另估|另報|另外報價|依實際|按次|按用量|加購|免費額度",
    "allowance": r"份文件|文件:|對話量:|每月 .*Token|免費試用|含 .*條|個自動化流程|[1-9][–~-][1-9] 流程|≤\d+步驟",
}


class PageText(HTMLParser):
    ignore = {"head", "script", "style", "svg", "noscript", "template"}
    blocks = {"br", "div", "section", "article", "h1", "h2", "h3", "h4", "h5",
              "p", "li", "td", "th", "dt", "dd", "tr", "summary", "main"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.ignore:
            self.hidden += 1
        elif not self.hidden and tag in self.blocks:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.ignore:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in self.blocks:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    def visible(self):
        lines = unicodedata.normalize("NFKC", "".join(self.parts)).splitlines()
        return "\n".join(" ".join(line.split()) for line in lines if line.strip())


def fetch(url, *, html):
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=25) as response:
        if urlsplit(response.geturl()).netloc != urlsplit(url).netloc:
            raise ValueError("來源網域改址，需覆核")
        mime = response.headers.get_content_type()
        if html and mime not in {"text/html", "application/xhtml+xml"}:
            raise ValueError("來源未回傳 HTML")
        raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError("來源頁面超過大小上限")
        return raw.decode(response.headers.get_content_charset() or "utf-8-sig"), sha256(raw).hexdigest()


def fetch_domain(item):
    """Visit each host sequentially and retain a result for every requested URL."""
    host, urls = item
    robots = RobotFileParser()
    try:
        try:
            rules, _ = fetch("https://" + host + "/robots.txt", html=False)
        except HTTPError as error:
            if error.code not in (404, 410):
                raise
            rules = ""
        robots.parse(rules.splitlines())
    except (OSError, ValueError, LookupError) as error:
        return {u: {"error": "robots.txt 無法核對：" + str(error)} for u in urls}
    interval = max(1, robots.crawl_delay(BOT) or 0)
    rate = robots.request_rate(BOT)
    if rate and rate.requests > 0:
        interval = max(interval, rate.seconds / rate.requests)
    result = {}
    next_visit = monotonic()
    for url in urls:
        try:
            if not robots.can_fetch(BOT, url):
                raise ValueError("robots.txt 不允許抓取")
            sleep(max(0, next_visit - monotonic()))
            next_visit = monotonic() + interval
            raw, digest = fetch(url, html=True)
            page = PageText()
            page.feed(raw)
            page.close()
            result[url] = {"text": page.visible(), "sha256": digest}
        except (OSError, ValueError, LookupError) as error:
            result[url] = {"error": str(error)}
            if isinstance(error, HTTPError) and error.code in (401, 403, 429):
                for rest in urls:
                    result.setdefault(rest, {"error": f"來源回應 HTTP {error.code}，同站停止抓取"})
                break
    return result


def collect_pages(offers):
    hosts = defaultdict(list)
    for url in dict.fromkeys(x.url for x in offers):
        hosts[urlsplit(url).netloc].append(url)
    pages = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for group in pool.map(fetch_domain, hosts.items()):
            pages.update(group)
    return pages


def target_section(text, bounds):
    starts = list(re.finditer(bounds[0], text, re.M))
    if len(starts) != 1:
        raise ValueError("目標方案起點缺漏或重複")
    end = re.compile(bounds[1], re.M).search(text, starts[0].end())
    if not end:
        raise ValueError("目標方案終點缺漏")
    return text[starts[0].start():end.start()]


def excerpt(text):
    line = " ".join(text.split())
    return line if len(line) <= 145 else line[:144] + "…"


def extract(offer, page):
    row = {"vendor": offer.vendor, "plan": offer.plan, "group": offer.group,
           "source": offer.url, "sha256": page.get("sha256"), "status": "review",
           "prices": {}, "price_evidence": {}, "terms": {}}
    if "error" in page:
        return {**row, "reason": page["error"]}
    try:
        section = target_section(page["text"], offer.section)
        if offer.group in (FLOW, KB) and PERIODIC.search(section):
            raise ValueError("發現可能強制的週期性費用，須重新分組")
        prices, evidence = {}, {}
        for unit, rule in offer.prices.items():
            matches = list(re.finditer(rule.replace("{N}", NUMBER), section, re.M))
            if len(matches) != 1:
                raise ValueError(f"{unit} 的指定方案、幣別、金額或計價單位缺漏或有多個匹配")
            match = matches[0]
            prices[unit] = int(match["twd"].replace(",", ""))
            evidence[unit] = " ".join(match.group().split())
        terms = {}
        for field, pattern in TERM_HINTS.items():
            samples = [excerpt(s) for s in section.splitlines() if re.search(pattern, s)][:3]
            for key, rule in offer.page_terms:
                if key == field:
                    samples.extend(excerpt(m.group()) for m in re.finditer(rule, page["text"], re.M))
            terms[field] = list(dict.fromkeys(samples)) or None
        return {**row, "status": "verified", "prices": prices, "price_evidence": evidence, "terms": terms}
    except ValueError as error:
        return {**row, "reason": str(error)}


def benchmark(rows, group):
    offers = [r for r in rows if r["group"] == group]
    if len({r["vendor"] for r in offers}) != len(offers):
        raise ValueError("同一供應商在同一建置類別出現兩次")
    prices = [(r["vendor"], r["prices"][UNIT_SETUP]) for r in offers if r["status"] == "verified"]
    values = [p for _, p in prices]
    result = {"expected": len(offers), "verified": len(prices),
              "mean_observed_twd": round(mean(values), 2) if values else None,
              "median_observed_twd": median(values) if values else None,
              "mean_retained_twd": None, "median_retained_twd": None}
    if len(prices) != len(offers) or len(prices) < 4:
        return {**result, "status": "incomplete" if len(prices) != len(offers) else "small_sample"}
    q1, _, q3 = quantiles(values, n=4, method="inclusive")
    step = 1.5 * (q3 - q1)
    low, high = q1 - step, q3 + step
    kept = [p for p in values if low <= p <= high]
    rejected = [{"vendor": v, "twd": p} for v, p in prices if p < low or p > high]
    return {**result, "status": "complete", "fences_twd": [low, high], "excluded": rejected,
            "retained": len(kept), "mean_retained_twd": round(mean(kept), 2),
            "median_retained_twd": median(kept)}


def save_report(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
        try:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True, help="此輪 JSON 報告的輸出路徑")
    args = cli.parse_args()
    pages = collect_pages(OFFERS)
    rows = [extract(o, pages[o.url]) for o in OFFERS]
    summary = {g: benchmark(rows, g) for g in (FLOW, KB)}
    save_report(args.output, {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
                              "currency": "TWD", "offers": rows, "benchmarks": summary})
    count = sum(r["status"] == "verified" for r in rows)
    print(f"已核對 {count}/{len(rows)} 筆。{args.output}")
    return 0 if count == len(rows) else 2


if __name__ == "__main__":
    sys.exit(main())
