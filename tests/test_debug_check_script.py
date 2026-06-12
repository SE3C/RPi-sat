import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
DEBUG_CHECK_PATH = ROOT / "scripts" / "debug_check.py"


def load_debug_check():
    module_name = "debug_check_under_test"
    spec = importlib.util.spec_from_file_location(module_name, DEBUG_CHECK_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class DebugCheckScriptTest(unittest.TestCase):
    def setUp(self):
        self.debug_check = load_debug_check()

    def test_discover_modules_keeps_base_modules_and_finds_project_python_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package").mkdir()
            (root / "package" / "__init__.py").write_text("", encoding="utf-8")
            (root / "package" / "worker.py").write_text("", encoding="utf-8")
            (root / ".hidden").mkdir()
            (root / ".hidden" / "ignored.py").write_text("", encoding="utf-8")

            with mock.patch.object(self.debug_check, "ROOT", root):
                modules = self.debug_check.discover_modules()

        self.assertEqual(
            modules[: len(self.debug_check.BASE_MODULES)],
            self.debug_check.BASE_MODULES,
        )
        self.assertIn("package", modules)
        self.assertIn("package.worker", modules)
        self.assertNotIn(".hidden.ignored", modules)
        self.assertEqual(len(modules), len(set(modules)))

    def test_validate_result_schema_accepts_valid_sensor_and_output_results(self):
        self.debug_check.validate_result_schema(
            "sensors.dht11",
            "read",
            {"status": "ok", "debug": {}},
        )
        self.debug_check.validate_result_schema(
            "output.led",
            "turn_on",
            {"ok": True, "device": "led", "action": "turn_on", "debug": {}},
        )

    def test_validate_result_schema_rejects_sensor_missing_required_keys(self):
        with self.assertRaisesRegex(KeyError, "missing 'status'"):
            self.debug_check.validate_result_schema(
                "sensors.dht11",
                "read",
                {"debug": {}},
            )

        with self.assertRaisesRegex(KeyError, "missing 'debug'"):
            self.debug_check.validate_result_schema(
                "sensors.dht11",
                "read",
                {"status": "ok"},
            )

    def test_validate_result_schema_rejects_output_missing_required_keys(self):
        with self.assertRaisesRegex(KeyError, "missing 'device'"):
            self.debug_check.validate_result_schema(
                "output.led",
                "turn_on",
                {"ok": True, "action": "turn_on", "debug": {}},
            )

        with self.assertRaisesRegex(KeyError, "missing 'errors'"):
            self.debug_check.validate_result_schema(
                "output.buzzer",
                "error_sound",
                {"ok": False, "device": "buzzer", "action": "error", "debug": {}},
            )

    def test_run_check_returns_passing_result_with_detail(self):
        result = self.debug_check.run_check("sample check", lambda: "ok detail")

        self.assertEqual(result.label, "sample check")
        self.assertTrue(result.passed)
        self.assertEqual(result.detail, "ok detail")

    def test_run_check_returns_failing_result_with_exception_detail(self):
        def failing_check():
            raise ValueError("bad value")

        result = self.debug_check.run_check("sample failure", failing_check)

        self.assertEqual(result.label, "sample failure")
        self.assertFalse(result.passed)
        self.assertEqual(result.detail, "ValueError: bad value")

    def test_main_prints_pass_summary_and_returns_zero(self):
        checks = [
            ("first check", lambda: "first detail"),
            ("second check", lambda: "second detail"),
        ]
        stdout = io.StringIO()

        with mock.patch.object(self.debug_check, "iter_checks", return_value=checks):
            with contextlib.redirect_stdout(stdout):
                exit_code = self.debug_check.main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("[PASS] first check - first detail", output)
        self.assertIn("[PASS] second check - second detail", output)
        self.assertIn("Summary: 2 PASS, 0 FAIL", output)


if __name__ == "__main__":
    unittest.main()
