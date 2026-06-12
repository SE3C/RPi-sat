"""GPS sensor reader for a NEO-6M module connected over UART.

The module is intentionally defensive: missing hardware, config, pyserial, or
pynmea2 should be reported in returned data instead of stopping the program.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

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


def _dependency_status() -> Dict[str, Dict[str, Any]]:
    return {
        "config": {
            "available": config is not None,
            "error": _CONFIG_ERROR,
        },
        "serial": {
            "available": serial is not None,
            "error": _SERIAL_ERROR,
        },
        "pynmea2": {
            "available": pynmea2 is not None,
            "error": _PYNMEA2_ERROR,
        },
    }


def _dependency_errors() -> List[str]:
    errors: List[str] = []
    for name, details in _dependency_status().items():
        if not details["available"]:
            errors.append(f"{name} unavailable: {details['error']}")
    return errors


def _safe_repr(value: Any) -> str:
    try:
        return repr(value)
    except Exception as exc:
        return f"<unrepresentable {type(value).__name__}: {type(exc).__name__}: {exc}>"


def _debug_details(
    port: Any = None,
    baudrate: Any = None,
    timeout: Any = None,
    max_sentences: Any = None,
    sentences_read: int = 0,
    last_raw_sentence: Optional[str] = None,
    parse_failure_reason: Optional[str] = None,
) -> Dict[str, Any]:
    dependencies = _dependency_status()
    return {
        "config_available": config is not None,
        "serial_available": serial is not None,
        "pynmea2_available": pynmea2 is not None,
        "dependencies": dependencies,
        "dependency_errors": _dependency_errors(),
        "port": port,
        "baudrate": baudrate,
        "timeout": timeout,
        "max_sentences": max_sentences,
        "sentences_read": sentences_read,
        "last_raw_sentence": last_raw_sentence,
        "parse_failure_reason": parse_failure_reason,
    }


def _sync_debug(result: Dict[str, Any]) -> Dict[str, Any]:
    debug = _debug_details(
        port=result.get("port"),
        baudrate=result.get("baudrate"),
        timeout=result.get("timeout"),
        max_sentences=result.get("max_sentences"),
        sentences_read=int(result.get("sentences_read") or 0),
        last_raw_sentence=result.get("last_raw_sentence"),
        parse_failure_reason=result.get("parse_failure_reason"),
    )
    result["debug"] = debug
    return result


def _empty_result(status: str = "error", error: Optional[str] = None) -> Dict[str, Any]:
    result = {
        "sensor": "GPS",
        "status": status,
        "latitude": None,
        "longitude": None,
        "altitude": None,
        "satellites": None,
        "raw": None,
        "error": error,
        "parse_failure_reason": None,
        "dependencies": _dependency_status(),
        "dependency_errors": _dependency_errors(),
        "config_available": config is not None,
        "serial_available": serial is not None,
        "pynmea2_available": pynmea2 is not None,
        "port": None,
        "baudrate": None,
        "timeout": None,
        "max_sentences": None,
        "sentences_read": 0,
        "last_raw_sentence": None,
    }
    return _sync_debug(result)


def parse_nmea_sentence(raw_sentence: str) -> Dict[str, Any]:
    """Parse one raw NMEA sentence and return available GPS fields.

    GGA sentences normally contain fix position, altitude, and satellite count.
    RMC sentences contain position but not altitude or satellite count.
    """
    result = _empty_result(status="no_fix")

    try:
        if isinstance(raw_sentence, bytes):
            raw_text = raw_sentence.decode("ascii", errors="replace").strip()
        elif raw_sentence is None:
            raw_text = ""
        else:
            raw_text = str(raw_sentence).strip()

        result["raw"] = raw_text
        result["last_raw_sentence"] = raw_text or None

        if not raw_text:
            result["status"] = "error"
            result["error"] = "empty NMEA sentence"
            result["parse_failure_reason"] = "empty NMEA sentence"
            return result

        if pynmea2 is None:
            error = f"pynmea2 unavailable: {_PYNMEA2_ERROR}"
            result["status"] = "error"
            result["error"] = error
            result["parse_failure_reason"] = error
            return result

        try:
            message = pynmea2.parse(raw_text)
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            result["status"] = "error"
            result["error"] = f"NMEA parse error: {reason}"
            result["parse_failure_reason"] = reason
            return result

        result["sentence_type"] = getattr(message, "sentence_type", None)
        result["talker"] = getattr(message, "talker", None)
        result["fix_quality"] = getattr(message, "gps_qual", None)
        result["fix_status"] = getattr(message, "status", None)

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
                    "satellites": int(satellites)
                    if satellites not in (None, "")
                    else None,
                    "error": None if has_position else "NMEA sentence has no position fix",
                    "parse_failure_reason": None,
                }
            )
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            result["status"] = "error"
            result["error"] = f"NMEA field extraction error: {reason}"
            result["parse_failure_reason"] = reason

        return result
    except Exception as exc:
        fallback = _empty_result(status="error")
        fallback["raw"] = _safe_repr(raw_sentence)
        fallback["error"] = f"unexpected NMEA parser failure: {type(exc).__name__}: {exc}"
        fallback["parse_failure_reason"] = f"{type(exc).__name__}: {exc}"
        return fallback


def _with_runtime_details(
    result: Dict[str, Any],
    port: Any,
    baudrate: Any,
    timeout: Any,
    max_sentences: Any,
    sentences_read: int,
    last_raw_sentence: Optional[str],
) -> Dict[str, Any]:
    result["dependencies"] = _dependency_status()
    result["dependency_errors"] = _dependency_errors()
    result["config_available"] = config is not None
    result["serial_available"] = serial is not None
    result["pynmea2_available"] = pynmea2 is not None
    result["port"] = port
    result["baudrate"] = baudrate
    result["timeout"] = timeout
    result["max_sentences"] = max_sentences
    result["sentences_read"] = sentences_read
    result["last_raw_sentence"] = last_raw_sentence
    return _sync_debug(result)


def read_gps(timeout: Optional[float] = None, max_sentences: int = 10) -> Dict[str, Any]:
    """Read GPS data from UART and return parsed position data when available."""
    try:
        port = _config_value("GPS_PORT", "gps_port", default="/dev/serial0")
        baudrate = _config_value("GPS_BAUDRATE", "gps_baudrate", default=9600)
        if timeout is None:
            timeout = _config_value("GPS_TIMEOUT_SECONDS", "gps_timeout_seconds", default=1.0)

        try:
            sentence_limit = int(max_sentences)
        except Exception:
            sentence_limit = 0

        sentences_read = 0
        last_raw_sentence: Optional[str] = None
        last_result = _with_runtime_details(
            _empty_result(status="no_data", error="no GPS sentences read"),
            port,
            baudrate,
            timeout,
            max_sentences,
            sentences_read,
            last_raw_sentence,
        )

        if serial is None:
            error = f"serial unavailable: {_SERIAL_ERROR}"
            last_result["status"] = "error"
            last_result["error"] = error
            return last_result

        if pynmea2 is None:
            error = f"pynmea2 unavailable: {_PYNMEA2_ERROR}"
            last_result["status"] = "error"
            last_result["error"] = error
            last_result["parse_failure_reason"] = error
            return last_result

        if sentence_limit <= 0:
            last_result["status"] = "error"
            last_result["error"] = f"invalid max_sentences: {max_sentences}"
            return last_result

        with serial.Serial(port=port, baudrate=baudrate, timeout=timeout) as uart:
            for _ in range(sentence_limit):
                try:
                    line = uart.readline()
                    if not line:
                        continue

                    if isinstance(line, bytes):
                        raw_sentence = line.decode("ascii", errors="replace").strip()
                    else:
                        raw_sentence = str(line).strip()
                    sentences_read += 1
                    last_raw_sentence = raw_sentence
                    parsed = parse_nmea_sentence(raw_sentence)
                    last_result = _with_runtime_details(
                        parsed,
                        port,
                        baudrate,
                        timeout,
                        max_sentences,
                        sentences_read,
                        last_raw_sentence,
                    )

                    if parsed["status"] == "ok":
                        return last_result
                except Exception as exc:
                    reason = f"{type(exc).__name__}: {exc}"
                    last_result = _with_runtime_details(
                        _empty_result(error=f"GPS read error: {reason}"),
                        port,
                        baudrate,
                        timeout,
                        max_sentences,
                        sentences_read,
                        last_raw_sentence,
                    )
                    return last_result
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        try:
            port
        except NameError:
            port = None
        try:
            baudrate
        except NameError:
            baudrate = None
        try:
            timeout
        except NameError:
            timeout = None
        try:
            max_sentences
        except NameError:
            max_sentences = None
        try:
            sentences_read
        except NameError:
            sentences_read = 0
        try:
            last_raw_sentence
        except NameError:
            last_raw_sentence = None
        last_result = _with_runtime_details(
            _empty_result(error=f"GPS serial connection error: {reason}"),
            port,
            baudrate,
            timeout,
            max_sentences,
            sentences_read,
            last_raw_sentence,
        )
        return last_result

    return last_result


def get_gps_data() -> Dict[str, Any]:
    """Compatibility wrapper for callers that expect a simple sensor function."""
    return read_gps()
