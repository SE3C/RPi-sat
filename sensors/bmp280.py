"""BMP280 temperature/pressure/altitude sensor reader.

The module is safe to import without I2C hardware or sensor libraries.
"""

from __future__ import annotations

import importlib.util


def _module_status(module_name):
    status = {"available": False, "path": None, "error": None}
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            status["error"] = "module not found"
        else:
            status["available"] = True
            status["path"] = spec.origin
    except Exception as exc:
        status["error"] = str(exc)
    return status


def _load_config():
    try:
        import config
    except Exception as exc:
        return None, str(exc)
    return config, None


def _config_value(*names, default=None):
    config, _ = _load_config()
    if config is None:
        return default
    for name in names:
        if hasattr(config, name):
            return getattr(config, name)
    return default


def _debug_template():
    config, config_error = _load_config()
    names = ("BMP280_I2C_ADDRESS", "I2C_BUS", "SEA_LEVEL_PRESSURE_HPA")
    values = {}
    for name in names:
        values[name] = getattr(config, name, None) if config is not None else None

    dependency_status = {
        "board": _module_status("board"),
        "busio": _module_status("busio"),
        "adafruit_bmp280": _module_status("adafruit_bmp280"),
        "bmp280": _module_status("bmp280"),
        "smbus2": _module_status("smbus2"),
    }

    return {
        "config": values,
        "config_error": config_error,
        "used_library": None,
        "used_library_path": None,
        "library_paths": {
            name: status["path"] for name, status in dependency_status.items()
        },
        "dependency_status": dependency_status,
        "attempted_readers": [],
        "errors": [],
    }


def _empty_reading(status="error", error=None, debug=None):
    if debug is None:
        debug = _debug_template()
    if error is not None and str(error) not in debug["errors"]:
        debug["errors"].append(str(error))

    data = {
        "sensor": "BMP280",
        "temperature": None,
        "pressure": None,
        "altitude": None,
        "status": status,
        "debug": debug,
    }
    if error is not None:
        data["error"] = str(error)
    return data


def _read_with_adafruit(address, sea_level_pressure, debug):
    import board
    import busio
    import adafruit_bmp280

    debug["library_paths"]["board"] = getattr(board, "__file__", None)
    debug["library_paths"]["busio"] = getattr(busio, "__file__", None)
    debug["library_paths"]["adafruit_bmp280"] = getattr(adafruit_bmp280, "__file__", None)

    i2c = busio.I2C(board.SCL, board.SDA)
    bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=address)
    if sea_level_pressure is not None:
        try:
            bmp280.sea_level_pressure = sea_level_pressure
        except Exception as exc:
            debug["errors"].append(f"adafruit sea level pressure setup failed: {exc}")

    return {
        "sensor": "BMP280",
        "temperature": float(bmp280.temperature),
        "pressure": float(bmp280.pressure),
        "altitude": float(bmp280.altitude),
        "status": "ok",
        "debug": debug,
    }


def _read_with_smbus2(address, bus_number, debug):
    import bmp280 as bmp280_module
    from smbus2 import SMBus

    debug["library_paths"]["bmp280"] = getattr(bmp280_module, "__file__", None)
    debug["library_paths"]["smbus2"] = importlib.util.find_spec("smbus2").origin

    bus = SMBus(bus_number)
    try:
        sensor = bmp280_module.BMP280(i2c_addr=address, i2c_dev=bus)
        temperature = sensor.get_temperature()
        pressure = sensor.get_pressure()
        altitude = sensor.get_altitude()
    finally:
        try:
            bus.close()
        except Exception:
            pass

    return {
        "sensor": "BMP280",
        "temperature": float(temperature),
        "pressure": float(pressure),
        "altitude": float(altitude),
        "status": "ok",
        "debug": debug,
    }


def read():
    """Return BMP280 temperature, pressure, altitude, status, and optional error."""
    debug = _debug_template()
    address = _config_value("BMP280_I2C_ADDRESS", default=0x76)
    bus_number = _config_value("I2C_BUS", default=1)
    sea_level_pressure = _config_value("SEA_LEVEL_PRESSURE_HPA", default=1013.25)

    errors = []
    readers = (
        ("adafruit_bmp280.Adafruit_BMP280_I2C", _read_with_adafruit),
        ("bmp280.BMP280+smbus2.SMBus", _read_with_smbus2),
    )
    for reader_name, reader in readers:
        debug["attempted_readers"].append(reader_name)
        try:
            if reader is _read_with_adafruit:
                result = reader(address, sea_level_pressure, debug)
            else:
                result = reader(address, bus_number, debug)
            debug["used_library"] = reader_name
            if reader is _read_with_adafruit:
                debug["used_library_path"] = debug["library_paths"]["adafruit_bmp280"]
            else:
                debug["used_library_path"] = debug["library_paths"]["bmp280"]
            return result
        except Exception as exc:
            message = f"{reader_name}: {exc}"
            errors.append(message)
            debug["errors"].append(message)

    return _empty_reading(error="; ".join(errors), debug=debug)


def read_sensor():
    return read()


def read_bmp280():
    return read()


def get_data():
    return read()


def get_sensor_data():
    return read()
