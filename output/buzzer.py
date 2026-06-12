"""Buzzer output helpers for audible CubeSat status signals."""

from __future__ import annotations

import time
import importlib.util
from pathlib import Path
from typing import Any

try:
    _CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.py"
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(f"{_CONFIG_PATH} does not exist")
    _SPEC = importlib.util.spec_from_file_location("config", _CONFIG_PATH)
    if _SPEC is None or _SPEC.loader is None:
        raise ImportError(f"cannot load config from {_CONFIG_PATH}")
    config = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(config)
except Exception as exc:  # pragma: no cover - depends on runtime layout
    config = None
    CONFIG_IMPORT_ERROR = str(exc)
else:
    CONFIG_IMPORT_ERROR = None

try:
    import RPi.GPIO as GPIO  # type: ignore
except Exception as exc:  # pragma: no cover - depends on installed hardware libs
    GPIO = None
    GPIO_IMPORT_ERROR = str(exc)
else:
    GPIO_IMPORT_ERROR = None


PIN_NAMES = ("BUZZER_PIN", "PIN_BUZZER")


def _result(action: str, ok: bool, **extra: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"ok": ok, "device": "buzzer", "action": action}
    data.update(extra)
    return data


def _get_pin() -> tuple[int | None, str | None]:
    if config is None:
        return None, f"config import failed: {CONFIG_IMPORT_ERROR}"

    for name in PIN_NAMES:
        if hasattr(config, name):
            return getattr(config, name), None

    return None, f"missing config pin for buzzer: one of {PIN_NAMES}"


def _setup_pin(pin: int) -> str | None:
    if GPIO is None:
        return f"GPIO import failed: {GPIO_IMPORT_ERROR}"

    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
    except Exception as exc:
        return str(exc)

    return None


def _write_pin(pin: int, value: bool) -> str | None:
    setup_error = _setup_pin(pin)
    if setup_error:
        return setup_error

    try:
        GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
    except Exception as exc:
        return str(exc)

    return None


def _beep_pattern(pattern: list[tuple[float, float]], action: str) -> dict[str, Any]:
    pin, pin_error = _get_pin()
    if pin_error:
        return _result(action, False, errors={"pin": pin_error})

    errors: list[str] = []
    for on_time, off_time in pattern:
        on_error = _write_pin(pin, True)
        if on_error:
            errors.append(on_error)
            break

        time.sleep(max(0.0, on_time))

        off_error = _write_pin(pin, False)
        if off_error:
            errors.append(off_error)
            break

        time.sleep(max(0.0, off_time))

    if not errors:
        final_off_error = _write_pin(pin, False)
        if final_off_error:
            errors.append(final_off_error)

    return _result(action, not errors, errors=errors)


def short_beep(duration: float = 0.1) -> dict[str, Any]:
    """Play one short beep."""
    return _beep_pattern([(duration, 0.0)], "short_beep")


def success_sound() -> dict[str, Any]:
    """Play two short beeps for success."""
    return _beep_pattern([(0.08, 0.08), (0.08, 0.0)], "success_sound")


def error_sound() -> dict[str, Any]:
    """Play one longer beep for error."""
    return _beep_pattern([(0.35, 0.0)], "error_sound")
