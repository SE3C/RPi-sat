"""LED output helpers for CubeSat status indicators.

The module is intentionally safe to import on development machines without
GPIO libraries or attached hardware.
"""

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


PIN_NAMES = {
    "red": ("LED_RED_PIN", "RED_LED_PIN", "PIN_LED_RED"),
    "green": ("LED_GREEN_PIN", "GREEN_LED_PIN", "PIN_LED_GREEN"),
    "yellow": ("LED_YELLOW_PIN", "YELLOW_LED_PIN", "PIN_LED_YELLOW"),
    "blue": ("LED_BLUE_PIN", "BLUE_LED_PIN", "PIN_LED_BLUE"),
}


def _result(action: str, ok: bool, **extra: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"ok": ok, "device": "led", "action": action}
    data.update(extra)
    return data


def _get_pin(color: str) -> tuple[int | None, str | None]:
    if config is None:
        return None, f"config import failed: {CONFIG_IMPORT_ERROR}"

    led_pins = getattr(config, "LED_PINS", None)
    if isinstance(led_pins, dict) and color in led_pins:
        return led_pins[color], None

    for name in PIN_NAMES[color]:
        if hasattr(config, name):
            return getattr(config, name), None

    return None, f"missing config pin for {color}: LED_PINS['{color}'] or one of {PIN_NAMES[color]}"


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


def all_off() -> dict[str, Any]:
    """Turn off every configured LED."""
    errors: dict[str, str] = {}

    for color in PIN_NAMES:
        pin, pin_error = _get_pin(color)
        if pin_error:
            errors[color] = pin_error
            continue

        write_error = _write_pin(pin, False)
        if write_error:
            errors[color] = write_error

    return _result("all_off", not errors, errors=errors)


def turn_on(color: str) -> dict[str, Any]:
    """Turn on a single LED by color and turn the others off."""
    normalized = color.lower().strip()
    if normalized not in PIN_NAMES:
        return _result(
            "turn_on",
            False,
            color=color,
            errors={"color": f"unsupported LED color: {color}"},
        )

    off_result = all_off()
    pin, pin_error = _get_pin(normalized)
    if pin_error:
        errors = dict(off_result.get("errors", {}))
        errors[normalized] = pin_error
        return _result("turn_on", False, color=normalized, errors=errors)

    write_error = _write_pin(pin, True)
    errors = dict(off_result.get("errors", {}))
    if write_error:
        errors[normalized] = write_error

    return _result("turn_on", not errors, color=normalized, errors=errors)


def show_standby() -> dict[str, Any]:
    """Show standby state with the blue LED."""
    return turn_on("blue")


def show_waiting() -> dict[str, Any]:
    """Show waiting/standby state with the blue LED."""
    return show_standby()


def show_success() -> dict[str, Any]:
    """Show success state with the green LED."""
    return turn_on("green")


def show_error() -> dict[str, Any]:
    """Show error state with the red LED."""
    return turn_on("red")


def blink(color: str, count: int = 1, interval: float = 0.2) -> dict[str, Any]:
    """Blink one LED without raising if GPIO is unavailable."""
    normalized = color.lower().strip()
    if normalized not in PIN_NAMES:
        return _result(
            "blink",
            False,
            color=color,
            errors={"color": f"unsupported LED color: {color}"},
        )

    errors: list[dict[str, Any]] = []
    for _ in range(max(0, count)):
        on_result = turn_on(normalized)
        if not on_result["ok"]:
            errors.append(on_result)
        time.sleep(max(0.0, interval))

        off_result = all_off()
        if not off_result["ok"]:
            errors.append(off_result)
        time.sleep(max(0.0, interval))

    return _result("blink", not errors, color=normalized, errors=errors)
