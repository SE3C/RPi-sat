"""DHT11 temperature/humidity sensor reader.

The module is safe to import on non-Raspberry Pi environments. Hardware
libraries are imported only when a reading is requested.
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
    names = ("DHT11_DATA_PIN", "DHT11_GPIO_PIN")
    values = {}
    for name in names:
        values[name] = getattr(config, name, None) if config is not None else None

    debug = {
        "config": values,
        "config_error": config_error,
        "used_library": None,
        "used_library_path": None,
        "library_paths": {},
        "dependency_status": {
            "Adafruit_DHT": _module_status("Adafruit_DHT"),
        },
        "attempted_readers": [],
        "errors": [],
    }
    debug["library_paths"]["Adafruit_DHT"] = debug["dependency_status"]["Adafruit_DHT"][
        "path"
    ]
    return debug


def _empty_reading(status="error", error=None, debug=None):
    if debug is None:
        debug = _debug_template()
    if error is not None:
        debug["errors"].append(str(error))

    data = {
        "sensor": "DHT11",
        "temperature": None,
        "humidity": None,
        "status": status,
        "debug": debug,
    }
    if error is not None:
        data["error"] = str(error)
    return data


def read():
    """Return DHT11 temperature, humidity, status, and optional error text."""
    debug = _debug_template()
    pin = _config_value("DHT11_GPIO_PIN", "DHT11_DATA_PIN", default=None)
    if pin is None:
        return _empty_reading(
            error="DHT11 GPIO pin is not defined in config.py",
            debug=debug,
        )

    reader_name = "Adafruit_DHT.read_retry"
    debug["attempted_readers"].append(reader_name)
    try:
        import Adafruit_DHT
    except Exception as exc:
        debug["dependency_status"]["Adafruit_DHT"]["available"] = False
        debug["dependency_status"]["Adafruit_DHT"]["error"] = str(exc)
        return _empty_reading(
            error=f"Adafruit_DHT import failed: {exc}",
            debug=debug,
        )

    try:
        debug["used_library"] = "Adafruit_DHT"
        debug["used_library_path"] = getattr(Adafruit_DHT, "__file__", None)
        debug["library_paths"]["Adafruit_DHT"] = debug["used_library_path"]
        humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, pin)
        if humidity is None or temperature is None:
            return _empty_reading(error="DHT11 returned no data", debug=debug)

        return {
            "sensor": "DHT11",
            "temperature": float(temperature),
            "humidity": float(humidity),
            "status": "ok",
            "debug": debug,
        }
    except Exception as exc:
        return _empty_reading(error=exc, debug=debug)


def read_sensor():
    return read()


def read_dht11():
    return read()


def get_data():
    return read()


def get_sensor_data():
    return read()
