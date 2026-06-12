"""Unit tests for GPIO-safe output device helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from output import buzzer, led


class OutputDeviceResultTests(unittest.TestCase):
    """Verify output helpers return structured errors without RPi.GPIO."""

    def assert_result_shape(
        self,
        result: dict,
        *,
        device: str,
        action: str,
    ) -> None:
        self.assertIsInstance(result, dict)
        for key in ("ok", "device", "action", "debug"):
            self.assertIn(key, result)

        self.assertIsInstance(result["ok"], bool)
        self.assertEqual(result["device"], device)
        self.assertEqual(result["action"], action)
        self.assertIsInstance(result["debug"], dict)

        if not result["ok"]:
            self.assertIn("errors", result)

    def test_led_helpers_return_dicts_without_gpio(self) -> None:
        cases = (
            ("all_off", led.all_off, (), {}),
            ("turn_on", led.turn_on, ("green",), {}),
            ("show_standby", led.show_standby, (), {}),
            ("show_waiting", led.show_waiting, (), {}),
            ("show_success", led.show_success, (), {}),
            ("show_error", led.show_error, (), {}),
            ("blink", led.blink, ("blue",), {"count": 1, "interval": 0}),
        )

        with (
            patch.object(led, "GPIO", None),
            patch.object(led, "GPIO_IMPORT_ERROR", "No module named RPi.GPIO"),
            patch.object(led.time, "sleep", return_value=None),
        ):
            for action, func, args, kwargs in cases:
                with self.subTest(action=action):
                    result = func(*args, **kwargs)
                    self.assert_result_shape(result, device="led", action=action)

    def test_buzzer_helpers_return_dicts_without_gpio(self) -> None:
        cases = (
            ("short_beep", buzzer.short_beep, (), {"duration": 0}),
            ("success_sound", buzzer.success_sound, (), {}),
            ("error_sound", buzzer.error_sound, (), {}),
        )

        with (
            patch.object(buzzer, "GPIO", None),
            patch.object(buzzer, "GPIO_IMPORT_ERROR", "No module named RPi.GPIO"),
            patch.object(buzzer.time, "sleep", return_value=None),
        ):
            for action, func, args, kwargs in cases:
                with self.subTest(action=action):
                    result = func(*args, **kwargs)
                    self.assert_result_shape(result, device="buzzer", action=action)


if __name__ == "__main__":
    unittest.main()
