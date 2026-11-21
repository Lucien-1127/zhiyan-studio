from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError

from collect import PageText, benchmark, extract, fetch_domain
from sources import FLOW, Offer, UNIT_SETUP


UNIT = Offer("工作室", "單一流程", FLOW, "https://example.com/price", (r"^單一流程$", r"^專案方案$"),
             {UNIT_SETUP: r"^NT\${N} 起\n每案$"})


def sample(*lines):
    parser = PageText()
    parser.feed("<script>NT$777 起</script><h3>單一流程</h3>"
                + "".join("<p>" + s + "</p>" for s in lines)
                + "<h3>專案方案</h3><p>NT$9,000 起</p><p>每案</p>")
    return extract(UNIT, {"text": parser.visible(), "sha256": "本測試使用本地範例"})


class PricingChecks(TestCase):
    def test_changed_price_and_unknown_support(self):
        self.assertEqual(sample("NT$18,500 起", "每案", "操作文件")["prices"][UNIT_SETUP], 18500)
        row = sample("NT$19,800 起", "每案", "操作文件")
        self.assertEqual(row["prices"][UNIT_SETUP], 19800)
        self.assertEqual(row["terms"]["features"], ["操作文件"])
        self.assertIsNone(row["terms"]["support"])

    def test_other_card_range_currency_or_time_unit_never_becomes_a_project_price(self):
        for price, unit in [("待議", "每案"), ("USD$12,000 起", "每案"), ("NT$18,000–28,000 起", "每案"),
                            ("NT$12,000 起", "每月"), ("NT$20,000 起/月", "每案")]:
            with self.subTest(price=price, unit=unit):
                self.assertEqual(sample(price, unit)["status"], "review")

    def test_ambiguous_offer_and_required_subscription_are_held(self):
        self.assertEqual(sample("NT$18,000 起", "每案", "NT$19,000 起", "每案")["status"], "review")
        self.assertEqual(sample("NT$18,000 起", "每案", "須搭配每月維護合約")["status"], "review")
        self.assertEqual(sample("NT$18,000 起", "每案", "單一流程")["status"], "review")

    def test_changed_source_never_substitutes_zero(self):
        self.assertEqual(extract(UNIT, {"error": "HTTP 403"})["prices"], {})
        row = extract(UNIT, {"text": "NT$12,000 起\n每案"})
        self.assertEqual((row["status"], row["prices"]), ("review", {}))

    def test_fixed_cohort_and_tukey_inclusive(self):
        amounts = [8000, 12000, 15000, 15000, 15000, 19900, 20000, 30000, 80000]
        rows = [{"vendor": str(i), "group": FLOW, "status": "verified", "prices": {UNIT_SETUP: price}}
                for i, price in enumerate(amounts)]
        rows.append({"vendor": "同頁訂閱", "group": "訂閱", "status": "verified", "prices": {"twd_per_month": 499}})
        stats = benchmark(rows, FLOW)
        self.assertEqual((stats["verified"], stats["retained"], stats["median_retained_twd"]), (9, 7, 15000))
        self.assertEqual((stats["mean_observed_twd"], stats["mean_retained_twd"]), (23877.78, 14985.71))
        self.assertEqual(benchmark(rows[:3], FLOW)["status"], "small_sample")
        with self.assertRaises(ValueError):
            benchmark(rows + [rows[0]], FLOW)
        rows[0]["status"] = "review"
        partial = benchmark(rows, FLOW)
        self.assertIsNone(partial["mean_retained_twd"])
        self.assertEqual((partial["status"], partial["verified"]), ("incomplete", 8))

    @patch("collect.fetch")
    def test_denied_source_stops_remaining_requests(self, fetch):
        urls = ["https://x.test/a", "https://x.test/b"]
        fetch.side_effect = [("User-agent: *\nAllow: /", "test"), HTTPError(urls[0], 429, "Too Many Requests", {}, None)]
        rows = fetch_domain(("x.test", urls))
        self.assertTrue(all("429" in rows[url]["error"] for url in urls))
        self.assertEqual(fetch.call_count, 2)

    @patch("collect.fetch", return_value=("User-agent: *\nDisallow: /plans", "test"))
    def test_robots_exclusion_is_honored(self, fetch):
        url = "https://x.test/plans"
        self.assertIn("robots.txt", fetch_domain(("x.test", [url]))[url]["error"])
        self.assertEqual(fetch.call_count, 1)
