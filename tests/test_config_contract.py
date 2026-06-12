"""Contract tests for shared hardware configuration values."""

from __future__ import annotations

import unittest

import config


class ConfigContractTests(unittest.TestCase):
    """Verify the public config module keeps the agreed wiring contract."""

    def test_bcm_gpio_pin_values(self) -> None:
        expected_pins = {
            "I2C_SDA_PIN": 2,
            "I2C_SCL_PIN": 3,
            "DHT11_DATA_PIN": 4,
            "DHT11_GPIO_PIN": 4,
            "DHT11_PIN": 4,
            "GPS_UART_TX_PIN": 14,
            "GPS_UART_RX_PIN": 15,
            "BUZZER_PIN": 24,
        }

        for name, expected_value in expected_pins.items():
            with self.subTest(name=name):
                self.assertTrue(hasattr(config, name))
                value = getattr(config, name)
                self.assertIsInstance(value, int)
                self.assertEqual(value, expected_value)

    def test_gps_serial_contract(self) -> None:
        self.assertEqual(config.GPS_PORT, "/dev/serial0")
        self.assertIsInstance(config.GPS_PORT, str)

        self.assertEqual(config.GPS_BAUDRATE, 9600)
        self.assertIsInstance(config.GPS_BAUDRATE, int)

        self.assertTrue(hasattr(config, "GPS_TIMEOUT_SECONDS"))
        self.assertIsInstance(config.GPS_TIMEOUT_SECONDS, (int, float))
        self.assertGreater(config.GPS_TIMEOUT_SECONDS, 0)

    def test_led_and_buzzer_contract(self) -> None:
        expected_led_pins = {
            "red": 17,
            "green": 27,
            "yellow": 22,
            "blue": 23,
        }

        self.assertIsInstance(config.LED_PINS, dict)
        self.assertEqual(config.LED_PINS, expected_led_pins)

        for color, pin in config.LED_PINS.items():
            with self.subTest(color=color):
                self.assertIsInstance(color, str)
                self.assertIsInstance(pin, int)

        self.assertEqual(config.BUZZER_PIN, 24)
        self.assertIsInstance(config.BUZZER_PIN, int)

    def test_i2c_contract(self) -> None:
        self.assertEqual(config.I2C_BUS, 1)
        self.assertIsInstance(config.I2C_BUS, int)

        expected_addresses = {
            "BMP280_I2C_ADDRESS": 0x76,
            "MPU6050_I2C_ADDRESS": 0x68,
            "BH1750_I2C_ADDRESS": 0x23,
        }

        for name, expected_value in expected_addresses.items():
            with self.subTest(name=name):
                self.assertTrue(hasattr(config, name))
                value = getattr(config, name)
                self.assertIsInstance(value, int)
                self.assertEqual(value, expected_value)

    def test_integration_settings_contract(self) -> None:
        self.assertTrue(hasattr(config, "INTEGRATION_INCLUDE_TRACEBACKS"))
        self.assertIsInstance(config.INTEGRATION_INCLUDE_TRACEBACKS, bool)

        self.assertTrue(hasattr(config, "INTEGRATION_RESULT_PREVIEW_CHARS"))
        self.assertIsInstance(config.INTEGRATION_RESULT_PREVIEW_CHARS, int)
        self.assertGreater(config.INTEGRATION_RESULT_PREVIEW_CHARS, 0)

    def test_non_i2c_gpio_pins_do_not_overlap(self) -> None:
        pin_groups = {
            "dht11": {config.DHT11_DATA_PIN},
            "led": set(config.LED_PINS.values()),
            "buzzer": {config.BUZZER_PIN},
        }

        seen: dict[int, str] = {}
        for group_name, pins in pin_groups.items():
            for pin in pins:
                with self.subTest(group=group_name, pin=pin):
                    self.assertNotIn(
                        pin,
                        seen,
                        f"GPIO BCM pin {pin} is shared by {seen.get(pin)} and {group_name}",
                    )
                    seen[pin] = group_name

        self.assertEqual({config.I2C_SDA_PIN, config.I2C_SCL_PIN}, {2, 3})


if __name__ == "__main__":
    unittest.main()
