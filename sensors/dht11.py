"""DHT11 temperature/humidity sensor reader.

The module is safe to import on non-Raspberry Pi environments. Hardware
libraries are imported only when a reading is requested.
"""


def _config_value(*names, default=None):
    try:
        import config
    except Exception:
        return default

    for name in names:
        if hasattr(config, name):
            return getattr(config, name)
    return default


def _empty_reading(status="error", error=None):
    data = {
        "sensor": "DHT11",
        "temperature": None,
        "humidity": None,
        "status": status,
    }
    if error is not None:
        data["error"] = str(error)
    return data


def read():
    """Return DHT11 temperature, humidity, status, and optional error text."""
    pin = _config_value("DHT11_GPIO_PIN", "DHT11_PIN", "DHT_GPIO_PIN", default=None)
    if pin is None:
        return _empty_reading(error="DHT11 GPIO pin is not defined in config.py")

    try:
        import Adafruit_DHT
    except Exception as exc:
        return _empty_reading(error=f"Adafruit_DHT import failed: {exc}")

    try:
        humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, pin)
        if humidity is None or temperature is None:
            return _empty_reading(error="DHT11 returned no data")

        return {
            "sensor": "DHT11",
            "temperature": float(temperature),
            "humidity": float(humidity),
            "status": "ok",
        }
    except Exception as exc:
        return _empty_reading(error=exc)


def read_sensor():
    return read()


def read_dht11():
    return read()


def get_data():
    return read()


def get_sensor_data():
    return read()
