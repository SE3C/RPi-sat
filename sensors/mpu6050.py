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
            "accelerometer": {"x": None, "y": None, "z": None},
            "gyroscope": {"x": None, "y": None, "z": None},
        },
        "conversion_constants": {
            "accelerometer_lsb_per_g": 16384.0,
            "gyroscope_lsb_per_deg_per_sec": 131.0,
        },
        "error_stage": error_stage,
    }


def _empty_result(status="error", error=None, debug=None):
    result = {
        "sensor": "MPU-6050",
        "status": status,
        "accelerometer": {"x": None, "y": None, "z": None, "unit": "g"},
        "gyroscope": {"x": None, "y": None, "z": None, "unit": "deg/s"},
        "orientation": {"roll": None, "pitch": None, "yaw": None, "unit": "deg"},
        "debug": debug or _debug_context(),
    }
    if error:
        result["error"] = str(error)
    return result


def _read_word(bus, address, register, debug=None, label=None):
    high = bus.read_byte_data(address, register)
    low = bus.read_byte_data(address, register + 1)
    value = (high << 8) | low
    unsigned_value = value
    if value >= 0x8000:
        value -= 0x10000

    if debug is not None:
        debug["register_reads"].append(
            {
                "label": label,
                "register": register,
                "register_hex": _format_address(register),
                "high_byte": high,
                "low_byte": low,
                "raw_unsigned": unsigned_value,
                "raw_signed": value,
            }
        )
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

    stage = "resolve_config"
    dependency_status = None

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

    debug = _debug_context(bus_number=bus_number, address=address)

    if address is None:
        debug["error_stage"] = stage
        return _empty_result(
            error="MPU-6050 I2C address is not defined in config.py",
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

        stage = "wake_sensor"
        bus.write_byte_data(address, PWR_MGMT_1, 0)
        debug["register_writes"].append(
            {
                "label": "power_management_1",
                "register": PWR_MGMT_1,
                "register_hex": _format_address(PWR_MGMT_1),
                "value": 0,
            }
        )
        time.sleep(0.05)

        stage = "read_accelerometer_x"
        raw_accel_x = _read_word(bus, address, ACCEL_XOUT_H, debug, "accel_x")
        stage = "read_accelerometer_y"
        raw_accel_y = _read_word(bus, address, ACCEL_XOUT_H + 2, debug, "accel_y")
        stage = "read_accelerometer_z"
        raw_accel_z = _read_word(bus, address, ACCEL_XOUT_H + 4, debug, "accel_z")

        stage = "read_gyroscope_x"
        raw_gyro_x = _read_word(bus, address, GYRO_XOUT_H, debug, "gyro_x")
        stage = "read_gyroscope_y"
        raw_gyro_y = _read_word(bus, address, GYRO_XOUT_H + 2, debug, "gyro_y")
        stage = "read_gyroscope_z"
        raw_gyro_z = _read_word(bus, address, GYRO_XOUT_H + 4, debug, "gyro_z")

        debug["raw_values"] = {
            "accelerometer": {
                "x": raw_accel_x,
                "y": raw_accel_y,
                "z": raw_accel_z,
            },
            "gyroscope": {"x": raw_gyro_x, "y": raw_gyro_y, "z": raw_gyro_z},
        }

        stage = "convert_values"
        accel_x = raw_accel_x / debug["conversion_constants"]["accelerometer_lsb_per_g"]
        accel_y = raw_accel_y / debug["conversion_constants"]["accelerometer_lsb_per_g"]
        accel_z = raw_accel_z / debug["conversion_constants"]["accelerometer_lsb_per_g"]

        gyro_x = raw_gyro_x / debug["conversion_constants"][
            "gyroscope_lsb_per_deg_per_sec"
        ]
        gyro_y = raw_gyro_y / debug["conversion_constants"][
            "gyroscope_lsb_per_deg_per_sec"
        ]
        gyro_z = raw_gyro_z / debug["conversion_constants"][
            "gyroscope_lsb_per_deg_per_sec"
        ]

        debug["error_stage"] = None

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


def read_mpu6050():
    return read_sensor()


def read():
    return read_sensor()


def get_data():
    return read_sensor()
