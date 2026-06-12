"""Integration-flow tests for main.py."""

from __future__ import annotations

import contextlib
import io
import sys
import types
import unittest
from unittest import mock

import main


class MainIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._module_names: list[str] = []

    def tearDown(self) -> None:
        for name in self._module_names:
            sys.modules.pop(name, None)

    def _install_module(self, name: str, **attributes: object) -> None:
        module = types.ModuleType(name)
        for attribute_name, value in attributes.items():
            setattr(module, attribute_name, value)
        sys.modules[name] = module
        self._module_names.append(name)

    def _assert_result_shape(self, result: dict[str, object], expected_device: str) -> None:
        for key in ("device", "target", "status", "ok", "stages", "duration_seconds"):
            self.assertIn(key, result)

        self.assertEqual(result["device"], expected_device)
        self.assertIsInstance(result["target"], str)
        self.assertIsInstance(result["status"], str)
        self.assertIsInstance(result["ok"], bool)
        self.assertIsInstance(result["stages"], list)
        self.assertIsInstance(result["duration_seconds"], float)

    def _assert_all_stage_names_recorded(self, result: dict[str, object]) -> None:
        stages = result["stages"]
        self.assertIsInstance(stages, list)
        self.assertEqual([stage["stage"] for stage in stages], list(main.STAGES))
        for stage in stages:
            self.assertIn("status", stage)
            self.assertIn("ok", stage)
            self.assertIn("duration_seconds", stage)

    def test_run_sensor_checks_returns_dict_and_records_every_task(self) -> None:
        self._install_module(
            "test_main_sensor_success",
            read_ok=lambda: {"ok": True, "status": "ready", "value": 42},
        )
        tasks = (
            ("TEST_SENSOR_A", "test_main_sensor_success", "read_ok"),
            ("TEST_SENSOR_B", "test_main_sensor_success", "read_ok"),
        )

        with mock.patch.object(main, "TASKS", tasks):
            results = main.run_sensor_checks()

        self.assertIsInstance(results, dict)
        self.assertEqual(set(results), {"TEST_SENSOR_A", "TEST_SENSOR_B"})
        for device, result in results.items():
            self._assert_result_shape(result, device)
            self._assert_all_stage_names_recorded(result)
            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "ok")

    def test_run_output_self_test_returns_dict_and_records_every_task(self) -> None:
        self._install_module(
            "test_main_output_success",
            show=lambda: {"ok": True, "status": "ok"},
            off=lambda: None,
        )
        tasks = (
            ("TEST_OUTPUT_SHOW", "test_main_output_success", "show"),
            ("TEST_OUTPUT_OFF", "test_main_output_success", "off"),
        )

        with mock.patch.object(main, "OUTPUT_TASKS", tasks):
            results = main.run_output_self_test()

        self.assertIsInstance(results, dict)
        self.assertEqual(set(results), {"TEST_OUTPUT_SHOW", "TEST_OUTPUT_OFF"})
        for device, result in results.items():
            self._assert_result_shape(result, device)
            self._assert_all_stage_names_recorded(result)
            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "ok")

    def test_failure_environments_record_module_import_callable_lookup_and_execution(self) -> None:
        self._install_module("test_main_non_callable", read_value="not callable")

        def raises_on_execution() -> None:
            raise RuntimeError("execution failed")

        self._install_module("test_main_execution_failure", read_fail=raises_on_execution)

        tasks = (
            ("IMPORT_FAIL", "test_main_missing_module_for_integration_test", "read"),
            ("LOOKUP_FAIL", "test_main_non_callable", "read_value"),
            ("EXECUTION_FAIL", "test_main_execution_failure", "read_fail"),
        )

        with mock.patch.object(main, "TASKS", tasks):
            results = main.run_sensor_checks()

        self.assertEqual(set(results), {"IMPORT_FAIL", "LOOKUP_FAIL", "EXECUTION_FAIL"})
        for device, result in results.items():
            self._assert_result_shape(result, device)
            self._assert_all_stage_names_recorded(result)
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "error")

        self.assertEqual(results["IMPORT_FAIL"]["error_stage"], "module_import")
        self.assertEqual(
            [stage["status"] for stage in results["IMPORT_FAIL"]["stages"]],
            ["error", "skipped", "skipped"],
        )
        self.assertEqual(results["LOOKUP_FAIL"]["error_stage"], "callable_lookup")
        self.assertEqual(
            [stage["status"] for stage in results["LOOKUP_FAIL"]["stages"]],
            ["ok", "error", "skipped"],
        )
        self.assertEqual(results["EXECUTION_FAIL"]["error_stage"], "execution")
        self.assertEqual(
            [stage["status"] for stage in results["EXECUTION_FAIL"]["stages"]],
            ["ok", "ok", "error"],
        )

    def test_main_runs_without_exception_and_prints_summary(self) -> None:
        self._install_module(
            "test_main_for_stdout",
            read=lambda: {"ok": True, "status": "ok"},
            show=lambda: {"ok": True},
        )
        sensor_tasks = (("STDOUT_SENSOR", "test_main_for_stdout", "read"),)
        output_tasks = (("STDOUT_OUTPUT", "test_main_for_stdout", "show"),)
        stdout = io.StringIO()

        with (
            mock.patch.object(main, "TASKS", sensor_tasks),
            mock.patch.object(main, "OUTPUT_TASKS", output_tasks),
            contextlib.redirect_stdout(stdout),
        ):
            main.main()

        output = stdout.getvalue()
        self.assertIn("CubeSat software integration check", output)
        self.assertIn("Sensor results: 1/1 ok, 0 error", output)
        self.assertIn("Output results: 1/1 ok, 0 error", output)
        self.assertIn("Overall summary: 2/2 ok, 0 error", output)


if __name__ == "__main__":
    unittest.main()
