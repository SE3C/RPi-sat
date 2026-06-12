"""MPU-6050 accelerometer/gyroscope reader.

The module is safe to import on machines without I2C libraries or hardware.
Call ``read_sensor()`` to get a dictionary that always contains sensor status.
"""

from __future__ import annotations

import time
import math


PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43


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
        "sensor": "MPU-6050",
        "status": status,
        "accelerometer": {"x": None, "y": None, "z": None, "unit": "g"},
        "gyroscope": {"x": None, "y": None, "z": None, "unit": "deg/s"},
        "orientation": {"roll": None, "pitch": None, "yaw": None, "unit": "deg"},
    }
    if error:
        result["error"] = str(error)
    return result


def _read_word(bus, address, register):
    high = bus.read_byte_data(address, register)
    low = bus.read_byte_data(address, register + 1)
    value = (high << 8) | low
    if value >= 0x8000:
        value -= 0x10000
    return value


def _estimate_orientation(accel_x, accel_y, accel_z):
    try:
        roll = math.degrees(math.atan2(accel_y, accel_z))
        pitch = math.degrees(
            math.atan2(-accel_x, math.sqrt((accel_y * accel_y) + (accel_z * accel_z)))
        )
    except Exception:
        roll = None
        pitch = None

    return {"roll": roll, "pitch": pitch, "yaw": None, "unit": "deg"}


def read_sensor(bus_number=None, address=None):
    """Return accelerometer, gyroscope, and status data from the MPU-6050."""

    if bus_number is None:
        bus_number = _config_value(("I2C_BUS", "I2C_BUS_NUMBER", "BUS_NUMBER"), 1)
    if address is None:
        address = _config_value(
            (
                "MPU6050_I2C_ADDRESS",
                "MPU_6050_I2C_ADDRESS",
                "MPU6050_ADDRESS",
                "MPU_6050_ADDRESS",
                "MPU6050_ADDR",
                "MPU_6050_ADDR",
            ),
            None,
        )

    if address is None:
        return _empty_result(error="MPU-6050 I2C address is not defined in config.py")

    SMBus, import_error = _load_smbus()
    if SMBus is None:
        return _empty_result(error=import_error)

    try:
        with SMBus(bus_number) as bus:
            bus.write_byte_data(address, PWR_MGMT_1, 0)
            time.sleep(0.05)

            accel_x = _read_word(bus, address, ACCEL_XOUT_H) / 16384.0
            accel_y = _read_word(bus, address, ACCEL_XOUT_H + 2) / 16384.0
            accel_z = _read_word(bus, address, ACCEL_XOUT_H + 4) / 16384.0

            gyro_x = _read_word(bus, address, GYRO_XOUT_H) / 131.0
            gyro_y = _read_word(bus, address, GYRO_XOUT_H + 2) / 131.0
            gyro_z = _read_word(bus, address, GYRO_XOUT_H + 4) / 131.0

        return {
            "sensor": "MPU-6050",
            "status": "ok",
            "accelerometer": {
                "x": accel_x,
                "y": accel_y,
                "z": accel_z,
                "unit": "g",
            },
            "gyroscope": {
                "x": gyro_x,
                "y": gyro_y,
                "z": gyro_z,
                "unit": "deg/s",
            },
            "orientation": _estimate_orientation(accel_x, accel_y, accel_z),
        }
    except Exception as error:
        return _empty_result(error=error)


def read_mpu6050():
    return read_sensor()


def read():
    return read_sensor()


def get_data():
    return read_sensor()
