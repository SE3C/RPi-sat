"""Tests for environment sensor readers without hardware dependencies."""

from __future__ import annotations

import builtins
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sensors import bmp280, dht11


MISSING_SENSOR_MODULES = {
    "Adafruit_DHT",
    "adafruit_bmp280",
    "bmp280",
    "board",
    "busio",
    "smbus2",
}


class EnvironmentSensorFallbackTests(unittest.TestCase):
    def call_without_external_sensor_libraries(self, func):
        """Run a reader as if no hardware-specific dependencies are installed."""
        real_import = builtins.__import__
        real_find_spec = importlib.util.find_spec

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            root_name = name.split(".", 1)[0]
            if name in MISSING_SENSOR_MODULES or root_name in MISSING_SENSOR_MODULES:
                raise ModuleNotFoundError(f"No module named '{name}'")
            return real_import(name, globals, locals, fromlist, level)

        def fake_find_spec(name, package=None):
            root_name = name.split(".", 1)[0]
            if name in MISSING_SENSOR_MODULES or root_name in MISSING_SENSOR_MODULES:
                return None
            return real_find_spec(name, package)

        with mock.patch("builtins.__import__", side_effect=fake_import), mock.patch(
            "importlib.util.find_spec", side_effect=fake_find_spec
        ):
            return func()

    def assert_common_sensor_result(self, result, sensor_name):
        self.assertIsInstance(result, dict)
        self.assertEqual(sensor_name, result.get("sensor"))
        self.assertIn("status", result)
        self.assertIn("debug", result)

        debug = result["debug"]
        self.assertIsInstance(debug, dict)
        self.assertIn("config", debug)
        self.assertIn("dependency_status", debug)
        self.assertIn("errors", debug)
        self.assertIn("attempted_readers", debug)

        self.assertIsInstance(debug["config"], dict)
        self.assertIsInstance(debug["dependency_status"], dict)
        self.assertIsInstance(debug["errors"], list)
        self.assertIsInstance(debug["attempted_readers"], list)

    def test_dht11_public_readers_return_debug_dict_without_dependencies(self):
        readers = (
            dht11.read,
            dht11.read_sensor,
            dht11.read_dht11,
            dht11.get_data,
            dht11.get_sensor_data,
        )

        for reader in readers:
            with self.subTest(reader=reader.__name__):
                result = self.call_without_external_sensor_libraries(reader)

                self.assert_common_sensor_result(result, "DHT11")
                debug = result["debug"]
                self.assertIn("Adafruit_DHT", debug["dependency_status"])
                self.assertFalse(debug["dependency_status"]["Adafruit_DHT"]["available"])
                self.assertIn("Adafruit_DHT.read_retry", debug["attempted_readers"])

    def test_bmp280_public_readers_return_debug_dict_without_dependencies(self):
        readers = (
            bmp280.read,
            bmp280.read_sensor,
            bmp280.read_bmp280,
            bmp280.get_data,
            bmp280.get_sensor_data,
        )

        for reader in readers:
            with self.subTest(reader=reader.__name__):
                result = self.call_without_external_sensor_libraries(reader)

                self.assert_common_sensor_result(result, "BMP280")
                debug = result["debug"]
                self.assertIn("adafruit_bmp280", debug["dependency_status"])
                self.assertIn("smbus2", debug["dependency_status"])
                self.assertFalse(
                    debug["dependency_status"]["adafruit_bmp280"]["available"]
                )
                self.assertFalse(debug["dependency_status"]["smbus2"]["available"])
                self.assertIn(
                    "adafruit_bmp280.Adafruit_BMP280_I2C",
                    debug["attempted_readers"],
                )
                self.assertIn("bmp280.BMP280+smbus2.SMBus", debug["attempted_readers"])


if __name__ == "__main__":
    unittest.main()
