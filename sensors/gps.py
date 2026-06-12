"""GPS sensor reader for a NEO-6M module connected over UART.

The module is intentionally defensive: missing hardware, config, pyserial, or
pynmea2 should be reported in returned data instead of stopping the program.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    import config  # type: ignore
except Exception as exc:  # pragma: no cover - depends on runtime deployment
    config = None  # type: ignore
    _CONFIG_ERROR: Optional[str] = str(exc)
else:
    _CONFIG_ERROR = None

try:
    import serial  # type: ignore
except Exception as exc:  # pragma: no cover - optional Raspberry Pi dependency
    serial = None  # type: ignore
    _SERIAL_ERROR: Optional[str] = str(exc)
else:
    _SERIAL_ERROR = None

try:
    import pynmea2  # type: ignore
except Exception as exc:  # pragma: no cover - optional parsing dependency
    pynmea2 = None  # type: ignore
    _PYNMEA2_ERROR: Optional[str] = str(exc)
else:
    _PYNMEA2_ERROR = None


def _config_value(*names: str, default: Any = None) -> Any:
    """Read a config value while tolerating absent or differently named fields."""
    if config is None:
        return default

    for name in names:
        if hasattr(config, name):
            return getattr(config, name)
    return default


def _empty_result(status: str = "error", error: Optional[str] = None) -> Dict[str, Any]:
    return {
        "status": status,
        "latitude": None,
        "longitude": None,
        "altitude": None,
        "satellites": None,
        "raw": None,
        "error": error,
    }


def parse_nmea_sentence(raw_sentence: str) -> Dict[str, Any]:
    """Parse one raw NMEA sentence and return available GPS fields.

    GGA sentences normally contain fix position, altitude, and satellite count.
    RMC sentences contain position but not altitude or satellite count.
    """
    result = _empty_result(status="no_fix")
    result["raw"] = raw_sentence

    if not raw_sentence:
        result["error"] = "empty NMEA sentence"
        return result

    if pynmea2 is None:
        result["error"] = f"pynmea2 unavailable: {_PYNMEA2_ERROR}"
        return result

    try:
        message = pynmea2.parse(raw_sentence.strip())
    except Exception as exc:
        result["status"] = "error"
        result["error"] = f"NMEA parse error: {exc}"
        return result

    try:
        latitude = getattr(message, "latitude", None)
        longitude = getattr(message, "longitude", None)
        altitude = getattr(message, "altitude", None)
        satellites = getattr(message, "num_sats", None)

        has_position = latitude is not None and longitude is not None
        result.update(
            {
                "status": "ok" if has_position else "no_fix",
                "latitude": latitude if has_position else None,
                "longitude": longitude if has_position else None,
                "altitude": altitude,
                "satellites": int(satellites) if satellites not in (None, "") else None,
                "error": None,
            }
        )
    except Exception as exc:
        result["status"] = "error"
        result["error"] = f"NMEA field extraction error: {exc}"

    return result


def read_gps(timeout: Optional[float] = None, max_sentences: int = 10) -> Dict[str, Any]:
    """Read GPS data from UART and return parsed position data when available."""
    port = _config_value("GPS_PORT", "gps_port", default="/dev/serial0")
    baudrate = _config_value("GPS_BAUDRATE", "gps_baudrate", default=9600)
    if timeout is None:
        timeout = _config_value("GPS_TIMEOUT_SECONDS", "gps_timeout_seconds", default=1.0)

    if _CONFIG_ERROR:
        result = _empty_result(error=f"config unavailable: {_CONFIG_ERROR}")
        result["port"] = port
        result["baudrate"] = baudrate
        return result

    if serial is None:
        result = _empty_result(error=f"serial unavailable: {_SERIAL_ERROR}")
        result["port"] = port
        result["baudrate"] = baudrate
        return result

    if pynmea2 is None:
        result = _empty_result(error=f"pynmea2 unavailable: {_PYNMEA2_ERROR}")
        result["port"] = port
        result["baudrate"] = baudrate
        return result

    last_result = _empty_result(status="no_data")
    last_result["port"] = port
    last_result["baudrate"] = baudrate

    try:
        with serial.Serial(port=port, baudrate=baudrate, timeout=timeout) as uart:
            for _ in range(max_sentences):
                try:
                    line = uart.readline()
                    if not line:
                        continue

                    raw_sentence = line.decode("ascii", errors="replace").strip()
                    parsed = parse_nmea_sentence(raw_sentence)
                    parsed["port"] = port
                    parsed["baudrate"] = baudrate
                    last_result = parsed

                    if parsed["status"] == "ok":
                        return parsed
                except Exception as exc:
                    last_result = _empty_result(error=f"GPS read error: {exc}")
                    last_result["port"] = port
                    last_result["baudrate"] = baudrate
                    return last_result
    except Exception as exc:
        last_result = _empty_result(error=f"GPS serial connection error: {exc}")
        last_result["port"] = port
        last_result["baudrate"] = baudrate
        return last_result

    return last_result


def get_gps_data() -> Dict[str, Any]:
    """Compatibility wrapper for callers that expect a simple sensor function."""
    return read_gps()
