"""BH1750 light sensor reader.

The module is safe to import on machines without I2C libraries or hardware.
Call ``read_sensor()`` to get a dictionary that always contains sensor status.
"""

from __future__ import annotations

import time


ONE_TIME_HIGH_RES_MODE = 0x20


def _config_value(names, default=None):
    try:
        import config
    except Exception:
        return default

    for name in names:
        try:
            if hasattr(config, name):
                return getattr(config, name)
        except Exception:
            return default
    return default


def _load_smbus():
    dependency_status = {
        "selected": None,
        "smbus2": {"available": False, "error": None},
        "smbus": {"available": False, "error": None},
    }

    try:
        from smbus2 import SMBus

        dependency_status["selected"] = "smbus2"
        dependency_status["smbus2"]["available"] = True
        return SMBus, dependency_status, None
    except Exception as first_error:
        dependency_status["smbus2"]["error"] = str(first_error)
        try:
            from smbus import SMBus

            dependency_status["selected"] = "smbus"
            dependency_status["smbus"]["available"] = True
            return SMBus, dependency_status, None
        except Exception as second_error:
            dependency_status["smbus"]["error"] = str(second_error)
            message = f"smbus2 unavailable: {first_error}; smbus unavailable: {second_error}"
            return None, dependency_status, message


def _format_address(address):
    if isinstance(address, int):
        return f"0x{address:02X}"
    return None


def _debug_context(bus_number=None, address=None, dependency_status=None, error_stage=None):
    return {
        "i2c_bus": bus_number,
        "address": address,
        "address_hex": _format_address(address),
        "dependency_status": dependency_status,
        "register_reads": [],
        "register_writes": [],
        "raw_values": {
            "bytes": None,
            "raw_lux": None,
        },
        "conversion_constants": {
            "lux_divisor": 1.2,
            "measurement_command": ONE_TIME_HIGH_RES_MODE,
        },
        "error_stage": error_stage,
    }


def _empty_result(status="error", error=None, debug=None):
    result = {
        "sensor": "BH1750",
        "status": status,
        "lux": None,
        "unit": "lux",
        "debug": debug or _debug_context(),
    }
    if error:
        result["error"] = str(error)
    return result


def read_sensor(bus_number=None, address=None):
    """Return illuminance in lux and status data from the BH1750."""

    stage = "resolve_config"
    dependency_status = None

    if bus_number is None:
        bus_number = _config_value(("I2C_BUS", "I2C_BUS_NUMBER", "BUS_NUMBER"), 1)
    if address is None:
        address = _config_value(
            ("BH1750_I2C_ADDRESS", "BH1750_ADDRESS", "BH1750_ADDR"), None
        )

    debug = _debug_context(bus_number=bus_number, address=address)

    if address is None:
        debug["error_stage"] = stage
        return _empty_result(
            error="BH1750 I2C address is not defined in config.py",
            debug=debug,
        )

    stage = "load_smbus"
    SMBus, dependency_status, import_error = _load_smbus()
    debug["dependency_status"] = dependency_status
    if SMBus is None:
        debug["error_stage"] = stage
        return _empty_result(error=import_error, debug=debug)

    bus = None
    try:
        stage = "open_bus"
        bus = SMBus(bus_number)

        stage = "start_measurement"
        bus.write_byte(address, ONE_TIME_HIGH_RES_MODE)
        debug["register_writes"].append(
            {
                "label": "one_time_high_resolution_mode",
                "register": ONE_TIME_HIGH_RES_MODE,
                "register_hex": _format_address(ONE_TIME_HIGH_RES_MODE),
                "value": ONE_TIME_HIGH_RES_MODE,
            }
        )
        time.sleep(0.18)

        stage = "read_measurement"
        data = bus.read_i2c_block_data(address, ONE_TIME_HIGH_RES_MODE, 2)
        debug["register_reads"].append(
            {
                "label": "illuminance",
                "register": ONE_TIME_HIGH_RES_MODE,
                "register_hex": _format_address(ONE_TIME_HIGH_RES_MODE),
                "length": 2,
                "bytes": list(data),
            }
        )

        stage = "convert_values"
        raw_value = (data[0] << 8) | data[1]
        debug["raw_values"] = {
            "bytes": list(data),
            "raw_lux": raw_value,
        }
        lux = raw_value / debug["conversion_constants"]["lux_divisor"]
        debug["error_stage"] = None

        return {
            "sensor": "BH1750",
            "status": "ok",
            "lux": lux,
            "unit": "lux",
            "debug": debug,
        }
    except Exception as error:
        debug["error_stage"] = stage
        return _empty_result(error=error, debug=debug)
    finally:
        if bus is not None and hasattr(bus, "close"):
            try:
                bus.close()
            except Exception:
                pass


def read_bh1750():
    return read_sensor()


def read():
    return read_sensor()


def get_data():
    return read_sensor()


class BH1750Sensor:
    """Compatibility wrapper for the team member Adafruit BH1750 API."""

    def __init__(self, i2c, address=0x23):
        self.sensor = None
        self.last_error = None

        try:
            import adafruit_bh1750

            self.sensor = adafruit_bh1750.BH1750(i2c, address=address)
        except Exception as exc:
            self.last_error = str(exc)

    def read(self):
        data = {
            "lux": None,
            "status": False,
            "error": self.last_error,
        }

        if self.sensor is None:
            return data

        try:
            data.update(
                {
                    "lux": self.sensor.lux,
                    "status": True,
                    "error": None,
                }
            )
        except Exception as exc:
            self.last_error = str(exc)
            data["error"] = self.last_error

        return data
