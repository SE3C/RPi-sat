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


def _empty_debug(action: str) -> dict[str, Any]:
    return {
        "action": action,
        "config": {
            "loaded": config is not None,
            "path": str(_CONFIG_PATH),
            "error": CONFIG_IMPORT_ERROR,
        },
        "gpio": {
            "imported": GPIO is not None,
            "error": GPIO_IMPORT_ERROR,
        },
        "pin_map": _pin_map(),
        "target_pin": None,
        "target_pins": {},
        "setup_errors": [],
        "write_errors": [],
    }


def _result(
    action: str,
    ok: bool,
    debug: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "ok": ok,
        "device": "led",
        "action": action,
        "debug": debug or _empty_debug(action),
    }
    data.update(extra)
    return data


def _pin_map() -> dict[str, int | None]:
    pins: dict[str, int | None] = {}
    led_pins = getattr(config, "LED_PINS", None) if config is not None else None

    for color, names in PIN_NAMES.items():
        pin = None
        if isinstance(led_pins, dict) and color in led_pins:
            pin = led_pins[color]
        elif config is not None:
            for name in names:
                if hasattr(config, name):
                    pin = getattr(config, name)
                    break
        pins[color] = pin

    return pins


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


def _setup_pin(pin: int, debug: dict[str, Any]) -> str | None:
    if GPIO is None:
        error = f"GPIO import failed: {GPIO_IMPORT_ERROR}"
        debug["setup_errors"].append({"pin": pin, "error": error})
        return error

    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
    except Exception as exc:
        error = str(exc)
        debug["setup_errors"].append({"pin": pin, "error": error})
        return error

    return None


def _write_pin(pin: int, value: bool, debug: dict[str, Any]) -> str | None:
    setup_error = _setup_pin(pin, debug)
    if setup_error:
        return setup_error

    try:
        GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
    except Exception as exc:
        error = str(exc)
        debug["write_errors"].append({"pin": pin, "value": value, "error": error})
        return error

    return None


def all_off() -> dict[str, Any]:
    """Turn off every configured LED."""
    action = "all_off"
    debug = _empty_debug(action)
    errors: dict[str, str] = {}

    for color in PIN_NAMES:
        pin, pin_error = _get_pin(color)
        if pin_error:
            errors[color] = pin_error
            continue

        debug["target_pins"][color] = pin
        write_error = _write_pin(pin, False, debug)
        if write_error:
            errors[color] = write_error

    return _result(action, not errors, debug=debug, errors=errors)


def _turn_on_color(color: str, action: str) -> dict[str, Any]:
    normalized = color.lower().strip()
    debug = _empty_debug(action)
    if normalized not in PIN_NAMES:
        return _result(
            action,
            False,
            debug=debug,
            color=color,
            errors={"color": f"unsupported LED color: {color}"},
        )

    off_result = all_off()
    debug["setup_errors"].extend(off_result["debug"].get("setup_errors", []))
    debug["write_errors"].extend(off_result["debug"].get("write_errors", []))
    debug["target_pins"] = dict(off_result["debug"].get("target_pins", {}))

    pin, pin_error = _get_pin(normalized)
    debug["target_pin"] = pin
    debug["target_pins"][normalized] = pin
    if pin_error:
        errors = dict(off_result.get("errors", {}))
        errors[normalized] = pin_error
        return _result(action, False, debug=debug, color=normalized, errors=errors)

    write_error = _write_pin(pin, True, debug)
    errors = dict(off_result.get("errors", {}))
    if write_error:
        errors[normalized] = write_error

    return _result(action, not errors, debug=debug, color=normalized, errors=errors)


def turn_on(color: str) -> dict[str, Any]:
    """Turn on a single LED by color and turn the others off."""
    return _turn_on_color(color, "turn_on")


def show_standby() -> dict[str, Any]:
    """Show standby state with the blue LED."""
    return _turn_on_color("blue", "show_standby")


def show_waiting() -> dict[str, Any]:
    """Show waiting/standby state with the blue LED."""
    return _turn_on_color("blue", "show_waiting")


def show_success() -> dict[str, Any]:
    """Show success state with the green LED."""
    return _turn_on_color("green", "show_success")


def show_error() -> dict[str, Any]:
    """Show error state with the red LED."""
    return _turn_on_color("red", "show_error")


def blink(color: str, count: int = 1, interval: float = 0.2) -> dict[str, Any]:
    """Blink one LED without raising if GPIO is unavailable."""
    action = "blink"
    normalized = color.lower().strip()
    debug = _empty_debug(action)
    if normalized not in PIN_NAMES:
        return _result(
            action,
            False,
            debug=debug,
            color=color,
            errors={"color": f"unsupported LED color: {color}"},
        )

    errors: list[dict[str, Any]] = []
    for _ in range(max(0, count)):
        on_result = turn_on(normalized)
        debug["setup_errors"].extend(on_result["debug"].get("setup_errors", []))
        debug["write_errors"].extend(on_result["debug"].get("write_errors", []))
        debug["target_pin"] = on_result["debug"].get("target_pin")
        debug["target_pins"].update(on_result["debug"].get("target_pins", {}))
        if not on_result["ok"]:
            errors.append(on_result)
        time.sleep(max(0.0, interval))

        off_result = all_off()
        debug["setup_errors"].extend(off_result["debug"].get("setup_errors", []))
        debug["write_errors"].extend(off_result["debug"].get("write_errors", []))
        debug["target_pins"].update(off_result["debug"].get("target_pins", {}))
        if not off_result["ok"]:
            errors.append(off_result)
        time.sleep(max(0.0, interval))

    return _result(action, not errors, debug=debug, color=normalized, errors=errors)
