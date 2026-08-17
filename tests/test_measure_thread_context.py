"""Unit tests for scripts/measure_thread_context.py (stdlib unittest)."""
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "measure_thread_context.py"
FIXTURES = ROOT / "tests" / "fixtures" / "sessions"
TMP_DIR = ROOT / "tests" / ".tmp_rollout_test"

DEFAULT_THREAD = "11111111-1111-4111-8111-111111111111"
TRIGGER_THREAD = "22222222-2222-4222-8222-222222222222"
ARCHIVE_THREAD = "33333333-3333-4333-8333-333333333333"
WARN_THREAD = "44444444-4444-4444-8444-444444444444"


def _load_module():
    spec = importlib.util.spec_from_file_location("measure_thread_context", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


m = _load_module()


def _scan(**kwargs):
    defaults = {
        "threshold_turn": 200_000,
        "threshold_cum": 10_000_000,
        "warn_occupancy": 0.80,
        "rollout_size_bytes": 5 * 1024 * 1024,
    }
    defaults.update(kwargs)
    return m.scan(str(FIXTURES), **defaults)


class ScanTest(unittest.TestCase):
    def test_reports_all_fixture_threads(self):
        report = _scan()
        self.assertEqual(len(report), 4)
        ids = {row["thread_id"] for row in report}
        self.assertEqual(ids, {DEFAULT_THREAD, TRIGGER_THREAD, ARCHIVE_THREAD, WARN_THREAD})

    def test_signal_flags(self):
        by_id = {row["thread_id"]: row for row in _scan()}
        self.assertEqual(by_id[DEFAULT_THREAD]["flags"], [])
        self.assertEqual(by_id[TRIGGER_THREAD]["flags"], ["TRIGGER"])
        self.assertEqual(by_id[ARCHIVE_THREAD]["flags"], ["ARCHIVE"])
        self.assertEqual(by_id[WARN_THREAD]["flags"], ["WARN"])

    def test_metrics(self):
        by_id = {row["thread_id"]: row for row in _scan()}
        self.assertEqual(by_id[TRIGGER_THREAD]["last_turn_delta"], 250_000)
        self.assertEqual(by_id[TRIGGER_THREAD]["cum_input"], 250_000)
        self.assertEqual(by_id[ARCHIVE_THREAD]["cum_input"], 10_050_100)
        self.assertLess(by_id[ARCHIVE_THREAD]["last_turn_delta"], 200_000)
        self.assertAlmostEqual(by_id[WARN_THREAD]["occupancy"], 0.9)
        self.assertEqual(by_id[WARN_THREAD]["turns"], 1)

    def test_rollout_signal(self):
        # Repo-local temp dir: writable in sandboxed local runs and in CI.
        TMP_DIR.mkdir(exist_ok=True)
        try:
            path = TMP_DIR / "rollout-55555555-5555-4555-8555-555555555555.jsonl"
            path.write_text(
                '{"timestamp":"t1","type":"event_msg","payload":{"type":"user_message"}}\n'
                '{"timestamp":"t2","type":"event_msg","payload":{"type":"token_count",'
                '"info":{"total_token_usage":{"input_tokens":100},'
                '"last_token_usage":{"input_tokens":50},"model_context_window":100000}}}\n',
                encoding="utf-8",
            )
            report = m.scan(str(TMP_DIR), rollout_size_bytes=1)
            self.assertEqual(len(report), 1)
            self.assertIn("ROLLOUT", report[0]["flags"])
            self.assertEqual(report[0]["rollout_bytes"], path.stat().st_size)
        finally:
            shutil.rmtree(TMP_DIR, ignore_errors=True)


class ExitCodeTest(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(m.exit_code_for([]), 0)
        self.assertEqual(m.exit_code_for([{"flags": ["TRIGGER"]}]), 1)
        self.assertEqual(m.exit_code_for([{"flags": ["WARN"]}]), 2)
        self.assertEqual(m.exit_code_for([{"flags": ["ARCHIVE"]}]), 3)
        self.assertEqual(m.exit_code_for([{"flags": ["ROLLOUT"]}]), 4)
        self.assertEqual(m.exit_code_for([{"flags": ["WARN"]}, {"flags": ["ARCHIVE"]}]), 3)


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_json_output(self):
        result = self.run_cli("--json", "--sessions", str(FIXTURES))
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(len(data), 4)
        self.assertIn("flags", data[0])

    def test_check_exit_archive(self):
        result = self.run_cli("--check", "--sessions", str(FIXTURES))
        self.assertEqual(result.returncode, 3)

    def test_check_exit_warn_with_raised_thresholds(self):
        result = self.run_cli(
            "--check",
            "--sessions",
            str(FIXTURES),
            "--threshold-turn",
            "999999999",
            "--threshold-cum",
            "999999999",
        )
        self.assertEqual(result.returncode, 2)

    def test_version(self):
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("0.1.0", result.stdout)


if __name__ == "__main__":
    unittest.main()