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
        if hasattr(config, name):
            return getattr(config, name)
    return default


def _load_smbus():
    try:
        from smbus2 import SMBus

        return SMBus, None
    except Exception as first_error:
        try:
            from smbus import SMBus

            return SMBus, None
        except Exception as second_error:
            message = f"smbus2 unavailable: {first_error}; smbus unavailable: {second_error}"
            return None, message


def _empty_result(status="error", error=None):
    result = {
        "sensor": "BH1750",
        "status": status,
        "lux": None,
        "unit": "lux",
    }
    if error:
        result["error"] = str(error)
    return result


def read_sensor(bus_number=None, address=None):
    """Return illuminance in lux and status data from the BH1750."""

    if bus_number is None:
        bus_number = _config_value(("I2C_BUS", "I2C_BUS_NUMBER", "BUS_NUMBER"), 1)
    if address is None:
        address = _config_value(
            ("BH1750_I2C_ADDRESS", "BH1750_ADDRESS", "BH1750_ADDR"), None
        )

    if address is None:
        return _empty_result(error="BH1750 I2C address is not defined in config.py")

    SMBus, import_error = _load_smbus()
    if SMBus is None:
        return _empty_result(error=import_error)

    try:
        with SMBus(bus_number) as bus:
            bus.write_byte(address, ONE_TIME_HIGH_RES_MODE)
            time.sleep(0.18)
            data = bus.read_i2c_block_data(address, ONE_TIME_HIGH_RES_MODE, 2)

        raw_value = (data[0] << 8) | data[1]
        lux = raw_value / 1.2

        return {
            "sensor": "BH1750",
            "status": "ok",
            "lux": lux,
            "unit": "lux",
        }
    except Exception as error:
        return _empty_result(error=error)


def read_bh1750():
    return read_sensor()


def read():
    return read_sensor()


def get_data():
    return read_sensor()
