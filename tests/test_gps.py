import unittest
from unittest import mock

from sensors import gps


class TestGpsSensor(unittest.TestCase):
    def assert_gps_result_shape(self, result):
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        self.assertEqual(result.get("sensor"), "GPS")
        self.assertIn("debug", result)

        debug = result["debug"]
        self.assertIsInstance(debug, dict)
        self.assertIn("port", debug)
        self.assertIn("baudrate", debug)
        self.assertIn("dependencies", debug)
        self.assertIn("dependency_errors", debug)

        dependencies = debug["dependencies"]
        self.assertIsInstance(dependencies, dict)
        for dependency in ("config", "serial", "pynmea2"):
            self.assertIn(dependency, dependencies)
            self.assertIn("available", dependencies[dependency])
            self.assertIn("error", dependencies[dependency])

    def test_parse_nmea_sentence_without_pynmea2_returns_error_dict(self):
        with mock.patch.object(gps, "pynmea2", None), mock.patch.object(
            gps, "_PYNMEA2_ERROR", "No module named 'pynmea2'"
        ):
            result = gps.parse_nmea_sentence(
                "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
            )

        self.assert_gps_result_shape(result)
        self.assertEqual(result["status"], "error")
        self.assertIn("pynmea2 unavailable", result["error"])
        self.assertFalse(result["debug"]["dependencies"]["pynmea2"]["available"])

    def test_parse_nmea_sentence_empty_input_returns_error_dict(self):
        result = gps.parse_nmea_sentence("")

        self.assert_gps_result_shape(result)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "empty NMEA sentence")
        self.assertEqual(result["debug"]["last_raw_sentence"], None)

    def test_read_gps_without_hardware_or_dependencies_returns_error_dict(self):
        with mock.patch.object(gps, "serial", None), mock.patch.object(
            gps, "_SERIAL_ERROR", "No module named 'serial'"
        ), mock.patch.object(gps, "pynmea2", None), mock.patch.object(
            gps, "_PYNMEA2_ERROR", "No module named 'pynmea2'"
        ):
            result = gps.read_gps(max_sentences=1)

        self.assert_gps_result_shape(result)
        self.assertEqual(result["status"], "error")
        self.assertIn("serial unavailable", result["error"])
        self.assertFalse(result["debug"]["dependencies"]["serial"]["available"])
        self.assertFalse(result["debug"]["dependencies"]["pynmea2"]["available"])
        self.assertIsNotNone(result["debug"]["port"])
        self.assertIsNotNone(result["debug"]["baudrate"])

    def test_read_gps_max_sentences_zero_returns_error_dict(self):
        fake_serial = mock.Mock()
        fake_pynmea2 = mock.Mock()

        with mock.patch.object(gps, "serial", fake_serial), mock.patch.object(
            gps, "pynmea2", fake_pynmea2
        ):
            result = gps.read_gps(max_sentences=0)

        self.assert_gps_result_shape(result)
        self.assertEqual(result["status"], "error")
        self.assertIn("invalid max_sentences: 0", result["error"])
        self.assertEqual(result["debug"]["max_sentences"], 0)
        fake_serial.Serial.assert_not_called()

    def test_get_gps_data_without_dependencies_returns_error_dict(self):
        with mock.patch.object(gps, "serial", None), mock.patch.object(
            gps, "_SERIAL_ERROR", "No module named 'serial'"
        ), mock.patch.object(gps, "pynmea2", None), mock.patch.object(
            gps, "_PYNMEA2_ERROR", "No module named 'pynmea2'"
        ):
            result = gps.get_gps_data()

        self.assert_gps_result_shape(result)
        self.assertEqual(result["status"], "error")
        self.assertIn("serial unavailable", result["error"])


if __name__ == "__main__":
    unittest.main()
