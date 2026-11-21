import unittest

from sync_evidence import count_articles, decode, prompt_counts, replace_block


class SnapshotTests(unittest.TestCase):
    def test_latest_edition_and_real_provisions(self):
        editions = {"20250701": {"1": "old", "2": "old"},
                    "_oldver": {"20200101": {"5": "old record"}},
                    "20260601": {"1": "含有刪除字樣的有效內文。", "2": "（刪除）", "2-1": "新條", "3": ""}}
        self.assertEqual(count_articles(editions), 2)

    def test_schema_drift_stops_refresh(self):
        for data in [{"current": {}}, {"20260230": {"1": "text"}}, {"20200101": {"1": None}}]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                count_articles(data)
        with self.assertRaises(ValueError):
            decode('{"1":"first","1":"later"}')

    def test_review_scenarios_and_test_methods_are_independent(self):
        source = """
class Helper:
    def test_helper(self): pass
class Checks(unittest.TestCase):
    def test_first(self): pass
    def helper(self): pass
"""
        self.assertEqual(prompt_counts(source, {"cases": [{"id": "a"}, {"id": "b"}]}),
                         {"tests": 1, "scenarios": 2})
        with self.assertRaises(ValueError):
            prompt_counts(source, {"cases": [{"id": "a"}, {"id": "a"}]})

    def test_missing_markers_never_overwrite_page(self):
        with self.assertRaises(ValueError):
            replace_block("<main>page</main>", "metrics")
