import builtins
import unittest
from unittest.mock import patch

from sensors import bh1750
from sensors import mpu6050


REQUIRED_DEBUG_KEYS = {
    "i2c_bus",
    "address",
    "address_hex",
    "dependency_status",
    "error_stage",
}


def import_without_smbus(name, globals=None, locals=None, fromlist=(), level=0):
    if name in {"smbus2", "smbus"}:
        raise ModuleNotFoundError(f"No module named '{name}'")
    return ORIGINAL_IMPORT(name, globals, locals, fromlist, level)


ORIGINAL_IMPORT = builtins.__import__


class MotionLightSensorTestCase(unittest.TestCase):
    def assert_dict_without_raising(self, reader):
        try:
            result = reader()
        except Exception as exc:  # pragma: no cover - failure path helper
            self.fail(f"{reader.__name__} raised {exc!r}")
        self.assertIsInstance(result, dict)
        return result

    def assert_debug_contract(self, result):
        self.assertIn("debug", result)
        self.assertIsInstance(result["debug"], dict)
        self.assertTrue(REQUIRED_DEBUG_KEYS.issubset(result["debug"].keys()))

    def assert_axis_contract(self, data, expected_unit):
        self.assertIsInstance(data, dict)
        self.assertEqual({"x", "y", "z", "unit"}, set(data.keys()))
        self.assertEqual(expected_unit, data["unit"])


class MissingSMBusDependencyTests(MotionLightSensorTestCase):
    def test_mpu6050_readers_return_dict_without_smbus_or_hardware(self):
        readers = (mpu6050.read_sensor, mpu6050.read_mpu6050)

        with patch("builtins.__import__", side_effect=import_without_smbus):
            for reader in readers:
                with self.subTest(reader=reader.__name__):
                    result = self.assert_dict_without_raising(reader)
                    self.assertIn("accelerometer", result)
                    self.assertIn("gyroscope", result)
                    self.assertIn("orientation", result)
                    self.assert_axis_contract(result["accelerometer"], "g")
                    self.assert_axis_contract(result["gyroscope"], "deg/s")
                    self.assertEqual(
                        {"roll", "pitch", "yaw", "unit"},
                        set(result["orientation"].keys()),
                    )
                    self.assertEqual("deg", result["orientation"]["unit"])
                    self.assert_debug_contract(result)
                    self.assertEqual("load_smbus", result["debug"]["error_stage"])

    def test_bh1750_readers_return_dict_without_smbus_or_hardware(self):
        readers = (
            bh1750.read,
            bh1750.read_sensor,
            bh1750.read_bh1750,
            bh1750.get_data,
        )

        with patch("builtins.__import__", side_effect=import_without_smbus):
            for reader in readers:
                with self.subTest(reader=reader.__name__):
                    result = self.assert_dict_without_raising(reader)
                    self.assertIn("lux", result)
                    self.assertIn("unit", result)
                    self.assertEqual("lux", result["unit"])
                    self.assert_debug_contract(result)
                    self.assertEqual("load_smbus", result["debug"]["error_stage"])


class FakeMPUSMBus:
    def __init__(self, bus_number):
        self.bus_number = bus_number
        self.closed = False
        self.writes = []
        self.registers = {
            0x3B: 0x40,
            0x3C: 0x00,
            0x3D: 0x00,
            0x3E: 0x00,
            0x3F: 0x40,
            0x40: 0x00,
            0x43: 0x00,
            0x44: 0x83,
            0x45: 0xFF,
            0x46: 0x7D,
            0x47: 0x00,
            0x48: 0x00,
        }

    def write_byte_data(self, address, register, value):
        self.writes.append((address, register, value))

    def read_byte_data(self, address, register):
        return self.registers[register]

    def close(self):
        self.closed = True


class FakeBH1750SMBus:
    def __init__(self, bus_number):
        self.bus_number = bus_number
        self.closed = False
        self.writes = []

    def write_byte(self, address, value):
        self.writes.append((address, value))

    def read_i2c_block_data(self, address, register, length):
        self.read_args = (address, register, length)
        return [0x01, 0x2C]

    def close(self):
        self.closed = True


class SuccessfulReadStructureTests(MotionLightSensorTestCase):
    def test_mpu6050_success_result_contains_motion_and_debug_structure(self):
        dependency_status = {
            "selected": "fake",
            "smbus2": {"available": False, "error": None},
            "smbus": {"available": False, "error": None},
        }

        with patch.object(
            mpu6050,
            "_load_smbus",
            return_value=(FakeMPUSMBus, dependency_status, None),
        ), patch.object(mpu6050.time, "sleep", return_value=None):
            result = mpu6050.read_sensor(bus_number=1, address=0x68)

        self.assertEqual("ok", result["status"])
        self.assert_axis_contract(result["accelerometer"], "g")
        self.assert_axis_contract(result["gyroscope"], "deg/s")
        self.assertEqual(
            {"roll", "pitch", "yaw", "unit"},
            set(result["orientation"].keys()),
        )
        self.assertEqual("deg", result["orientation"]["unit"])
        self.assertAlmostEqual(1.0, result["accelerometer"]["x"])
        self.assertAlmostEqual(0.0, result["accelerometer"]["y"])
        self.assertAlmostEqual(1.0, result["accelerometer"]["z"])
        self.assertAlmostEqual(1.0, result["gyroscope"]["x"])
        self.assertAlmostEqual(-1.0, result["gyroscope"]["y"])
        self.assertAlmostEqual(0.0, result["gyroscope"]["z"])
        self.assertAlmostEqual(0.0, result["orientation"]["roll"])
        self.assertAlmostEqual(-45.0, result["orientation"]["pitch"])
        self.assertIsNone(result["orientation"]["yaw"])
        self.assert_debug_contract(result)
        self.assertEqual(1, result["debug"]["i2c_bus"])
        self.assertEqual(0x68, result["debug"]["address"])
        self.assertEqual("0x68", result["debug"]["address_hex"])
        self.assertEqual(dependency_status, result["debug"]["dependency_status"])
        self.assertIsNone(result["debug"]["error_stage"])

    def test_bh1750_success_result_contains_lux_and_debug_structure(self):
        dependency_status = {
            "selected": "fake",
            "smbus2": {"available": False, "error": None},
            "smbus": {"available": False, "error": None},
        }

        with patch.object(
            bh1750,
            "_load_smbus",
            return_value=(FakeBH1750SMBus, dependency_status, None),
        ), patch.object(bh1750.time, "sleep", return_value=None):
            result = bh1750.read_sensor(bus_number=1, address=0x23)

        self.assertEqual("ok", result["status"])
        self.assertIn("lux", result)
        self.assertEqual("lux", result["unit"])
        self.assertAlmostEqual(250.0, result["lux"])
        self.assert_debug_contract(result)
        self.assertEqual(1, result["debug"]["i2c_bus"])
        self.assertEqual(0x23, result["debug"]["address"])
        self.assertEqual("0x23", result["debug"]["address_hex"])
        self.assertEqual(dependency_status, result["debug"]["dependency_status"])
        self.assertIsNone(result["debug"]["error_stage"])


if __name__ == "__main__":
    unittest.main()
