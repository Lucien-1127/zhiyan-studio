"""Offline acceptance checks. Run directly with Python 3.9 or newer."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
from review import check_contract, render_handoff, render_skill


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "references/interview.json"
EXAMPLE = json.loads(SAMPLE.read_text(encoding="utf-8"))


def run(*args):
    return subprocess.run([sys.executable, str(ROOT / "scripts/review.py"), *args],
                          capture_output=True, text=True, check=False)


class DeliveryTests(unittest.TestCase):
    def test_usable_example_and_pending_handoff(self):
        self.assertEqual(check_contract(EXAMPLE), [])
        self.assertIn("transcript", render_skill(EXAMPLE))
        packet = render_handoff(EXAMPLE)
        for case in EXAMPLE["cases"].values():
            self.assertIn(case["expected"], packet)
        self.assertEqual(packet.count("實際輸出與紀錄：待執行"), 3)

    def test_injected_faults(self):
        faults = [
            ("VAGUE_TRIGGER", lambda d: d["activation"].update(include=["幫我處理！"])),
            ("TRIGGER_CONFLICT", lambda d: d["activation"]["exclude"].append(d["activation"]["include"][0] + "。")),
            ("RULE_CONFLICT", lambda d: d["allow"].append("send-email")),
            ("UNAUTHORIZED_STEP", lambda d: d["steps"][0].update(action="send-email")),
            ("MISSING_SOURCE", lambda d: d["steps"].reverse()),
            ("OVERWRITE", lambda d: d["steps"][0].update(write=["transcript"])),
            ("MISSING_OUTPUT", lambda d: d["outputs"].update(extra="CSV 工作清單")),
            ("FRAGILE_STEP", lambda d: d["steps"][0].update(instruction="適當處理")),
            ("FAILURE_HANDLING", lambda d: d["steps"][0].pop("failure")),
            ("UNBOUNDED_RETRY", lambda d: d["steps"][0]["failure"].update(then="持續重試直到成功")),
            ("ACCEPTANCE_CASE", lambda d: d["cases"].pop("outside_scope")),
            ("FORMAT", lambda d: d.update(outputs="交件就好")),
        ]
        for code, mutate in faults:
            with self.subTest(code=code):
                data = deepcopy(EXAMPLE)
                mutate(data)
                self.assertIn(code, {e["code"] for e in check_contract(data)})

    def test_bounded_read_only_retry(self):
        data = deepcopy(EXAMPLE)
        data["steps"][0]["failure"] = {
            "when": "唯讀檔案暫時無法讀取", "then": "重試讀取該檔案。",
            "retry": {"limit": 1, "repeat_safe": "僅讀取既有檔案", "exhausted": "停止並請接手者檢查檔案"},
        }
        self.assertEqual(check_contract(data), [])
        self.assertIn("至多重試 1 次", render_skill(data))
        data["steps"][0]["failure"]["then"] = "持續重試直到成功。"
        self.assertIn("UNBOUNDED_RETRY", {e["code"] for e in check_contract(data)})
        data["steps"][0]["failure"]["then"] = "核對目前狀態，禁止無限重試。"
        self.assertEqual(check_contract(data), [])
        data["steps"][0]["failure"]["retry"]["limit"] = True
        self.assertIn("UNBOUNDED_RETRY", {e["code"] for e in check_contract(data)})

    def test_cli_verify_and_drift(self):
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / "SKILL.md"
            generated = run(SAMPLE, "--emit", "skill")
            self.assertEqual(generated.returncode, 0, generated.stderr)
            output.write_text(generated.stdout, encoding="utf-8")
            self.assertEqual(run(SAMPLE, "--verify", output).returncode, 0)
            output.write_text(generated.stdout + "新增寄信步驟。\n", encoding="utf-8")
            altered = run(SAMPLE, "--verify", output)
            self.assertEqual(altered.returncode, 1)
            self.assertEqual(json.loads(altered.stdout)["issues"][0]["code"], "SPEC_DRIFT")

    def test_cli_invalid_input_never_emits_partial_skill(self):
        with tempfile.TemporaryDirectory() as scratch:
            source = Path(scratch) / "contract.json"
            for raw, exit_code in [('{"name":', 2), ('{"name":"first","name":"second"}', 2),
                                   ('[]', 1), ('{"name":"invalid-contract"}', 1)]:
                with self.subTest(raw=raw):
                    source.write_text(raw, encoding="utf-8")
                    result = run(source, "--emit", "skill")
                    self.assertEqual(result.returncode, exit_code)
                    self.assertFalse(result.stdout)
                    self.assertIn("status", json.loads(result.stderr))


if __name__ == "__main__":
    unittest.main(verbosity=2)
