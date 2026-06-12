"""BMP280 temperature/pressure/altitude sensor reader.

The module is safe to import without I2C hardware or sensor libraries.
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
        "sensor": "BMP280",
        "temperature": None,
        "pressure": None,
        "altitude": None,
        "status": status,
    }
    if error is not None:
        data["error"] = str(error)
    return data


def _read_with_adafruit(address):
    import board
    import busio
    import adafruit_bmp280

    i2c = busio.I2C(board.SCL, board.SDA)
    bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=address)

    return {
        "sensor": "BMP280",
        "temperature": float(bmp280.temperature),
        "pressure": float(bmp280.pressure),
        "altitude": float(bmp280.altitude),
        "status": "ok",
    }


def _read_with_smbus2(address):
    import bmp280
    from smbus2 import SMBus

    bus_number = _config_value("BMP280_I2C_BUS", "I2C_BUS", default=1)
    bus = SMBus(bus_number)
    try:
        sensor = bmp280.BMP280(i2c_addr=address, i2c_dev=bus)
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
    }


def read():
    """Return BMP280 temperature, pressure, altitude, status, and optional error."""
    address = _config_value("BMP280_I2C_ADDRESS", "BMP280_ADDRESS", "BMP280_ADDR", default=0x76)

    errors = []
    for reader in (_read_with_adafruit, _read_with_smbus2):
        try:
            return reader(address)
        except Exception as exc:
            errors.append(f"{reader.__name__}: {exc}")

    return _empty_reading(error="; ".join(errors))


def read_sensor():
    return read()


def read_bmp280():
    return read()


def get_data():
    return read()


def get_sensor_data():
    return read()
