#!/usr/bin/env python3
"""Local validation script for development machines without Raspberry Pi hardware."""

from __future__ import annotations

import importlib
import inspect
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]

BASE_MODULES = (
    "config",
    "main",
    "sensors",
    "sensors.gps",
    "sensors.dht11",
    "sensors.bmp280",
    "sensors.mpu6050",
    "sensors.bh1750",
    "output",
    "output.led",
    "output.buzzer",
)

REQUIRED_FUNCTIONS = {
    "main": (
        "run_sensor_checks",
        "run_output_self_test",
        "main",
    ),
    "sensors.gps": (
        "parse_nmea_sentence",
        "read_gps",
        "get_gps_data",
    ),
    "sensors.dht11": (
        "read",
        "read_sensor",
        "read_dht11",
        "get_data",
        "get_sensor_data",
    ),
    "sensors.bmp280": (
        "read",
        "read_sensor",
        "read_bmp280",
        "get_data",
        "get_sensor_data",
    ),
    "sensors.mpu6050": (
        "read",
        "read_sensor",
        "read_mpu6050",
        "get_data",
    ),
    "sensors.bh1750": (
        "read",
        "read_sensor",
        "read_bh1750",
        "get_data",
    ),
    "output.led": (
        "all_off",
        "turn_on",
        "show_standby",
        "show_waiting",
        "show_success",
        "show_error",
        "blink",
    ),
    "output.buzzer": (
        "short_beep",
        "success_sound",
        "error_sound",
    ),
}

CALL_CHECKS = (
    ("main", "run_sensor_checks", (), {}),
    ("main", "run_output_self_test", (), {}),
    ("sensors.gps", "parse_nmea_sentence", ("",), {}),
    ("sensors.gps", "read_gps", (), {"max_sentences": 0}),
    ("sensors.gps", "get_gps_data", (), {}),
    ("sensors.dht11", "read", (), {}),
    ("sensors.dht11", "read_sensor", (), {}),
    ("sensors.dht11", "read_dht11", (), {}),
    ("sensors.dht11", "get_data", (), {}),
    ("sensors.dht11", "get_sensor_data", (), {}),
    ("sensors.bmp280", "read", (), {}),
    ("sensors.bmp280", "read_sensor", (), {}),
    ("sensors.bmp280", "read_bmp280", (), {}),
    ("sensors.bmp280", "get_data", (), {}),
    ("sensors.bmp280", "get_sensor_data", (), {}),
    ("sensors.mpu6050", "read", (), {}),
    ("sensors.mpu6050", "read_sensor", (), {}),
    ("sensors.mpu6050", "read_mpu6050", (), {}),
    ("sensors.mpu6050", "get_data", (), {}),
    ("sensors.bh1750", "read", (), {}),
    ("sensors.bh1750", "read_sensor", (), {}),
    ("sensors.bh1750", "read_bh1750", (), {}),
    ("sensors.bh1750", "get_data", (), {}),
    ("output.led", "all_off", (), {}),
    ("output.led", "turn_on", ("red",), {}),
    ("output.led", "show_standby", (), {}),
    ("output.led", "show_waiting", (), {}),
    ("output.led", "show_success", (), {}),
    ("output.led", "show_error", (), {}),
    ("output.led", "blink", ("red",), {"count": 0, "interval": 0}),
    ("output.buzzer", "short_beep", (), {"duration": 0}),
    ("output.buzzer", "success_sound", (), {}),
    ("output.buzzer", "error_sound", (), {}),
)

SENSOR_MODULES = {
    "sensors.gps",
    "sensors.dht11",
    "sensors.bmp280",
    "sensors.mpu6050",
    "sensors.bh1750",
}

OUTPUT_MODULES = {
    "output.led",
    "output.buzzer",
}


@dataclass
class CheckResult:
    label: str
    passed: bool
    detail: str = ""


def add_project_root_to_path() -> None:
    root_text = str(ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)


def format_exception(exc: BaseException) -> str:
    final_line = traceback.format_exception_only(type(exc), exc)[-1].strip()
    return final_line or repr(exc)


def run_check(label: str, check: Callable[[], str]) -> CheckResult:
    try:
        detail = check()
    except Exception as exc:
        return CheckResult(label=label, passed=False, detail=format_exception(exc))
    return CheckResult(label=label, passed=True, detail=detail)


def import_module(module_name: str) -> Any:
    return importlib.import_module(module_name)


def module_name_from_path(path: Path) -> str | None:
    relative = path.relative_to(ROOT)
    if relative.parts[0].startswith("."):
        return None
    if path == Path(__file__).resolve():
        return None
    if relative.name == "__init__.py":
        return ".".join(relative.parent.parts) if relative.parent.parts else None
    return ".".join(relative.with_suffix("").parts)


def discover_modules() -> tuple[str, ...]:
    modules = list(BASE_MODULES)
    for path in sorted(ROOT.rglob("*.py")):
        if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
            continue
        module_name = module_name_from_path(path)
        if module_name and module_name not in modules:
            modules.append(module_name)
    return tuple(modules)


def check_import(module_name: str) -> str:
    module = import_module(module_name)
    location = getattr(module, "__file__", "built-in")
    return str(location)


def check_required_function(module_name: str, function_name: str) -> str:
    module = import_module(module_name)
    candidate = getattr(module, function_name)
    if not callable(candidate):
        raise TypeError(f"{module_name}.{function_name} exists but is not callable")
    signature = ""
    try:
        signature = str(inspect.signature(candidate))
    except Exception:
        signature = "(signature unavailable)"
    return f"callable {module_name}.{function_name}{signature}"


def check_function_call(
    module_name: str,
    function_name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    module = import_module(module_name)
    candidate = getattr(module, function_name)
    result = candidate(*args, **kwargs)
    validate_result_schema(module_name, function_name, result)
    return f"returned {type(result).__name__}"


def validate_result_schema(module_name: str, function_name: str, result: Any) -> None:
    if module_name == "main":
        if not isinstance(result, dict):
            raise TypeError(f"{module_name}.{function_name} returned {type(result).__name__}, expected dict")
        return

    if module_name in SENSOR_MODULES:
        if not isinstance(result, dict):
            raise TypeError(f"{module_name}.{function_name} returned {type(result).__name__}, expected dict")
        for key in ("status", "debug"):
            if key not in result:
                raise KeyError(f"{module_name}.{function_name} result missing {key!r}")
        if not isinstance(result["debug"], dict):
            raise TypeError(f"{module_name}.{function_name} debug must be dict")
        return

    if module_name in OUTPUT_MODULES:
        if not isinstance(result, dict):
            raise TypeError(f"{module_name}.{function_name} returned {type(result).__name__}, expected dict")
        for key in ("ok", "device", "action", "debug"):
            if key not in result:
                raise KeyError(f"{module_name}.{function_name} result missing {key!r}")
        if not isinstance(result["debug"], dict):
            raise TypeError(f"{module_name}.{function_name} debug must be dict")
        if result.get("ok") is False and "errors" not in result:
            raise KeyError(f"{module_name}.{function_name} error result missing 'errors'")


def iter_checks() -> list[tuple[str, Callable[[], str]]]:
    checks: list[tuple[str, Callable[[], str]]] = []

    for module_name in discover_modules():
        checks.append(
            (
                f"import {module_name}",
                lambda module_name=module_name: check_import(module_name),
            )
        )

    for module_name, function_names in REQUIRED_FUNCTIONS.items():
        for function_name in function_names:
            checks.append(
                (
                    f"required function {module_name}.{function_name}",
                    lambda module_name=module_name, function_name=function_name: (
                        check_required_function(module_name, function_name)
                    ),
                )
            )

    for module_name, function_name, args, kwargs in CALL_CHECKS:
        checks.append(
            (
                f"call {module_name}.{function_name}",
                lambda module_name=module_name,
                function_name=function_name,
                args=args,
                kwargs=kwargs: check_function_call(
                    module_name,
                    function_name,
                    args,
                    kwargs,
                ),
            )
        )

    return checks


def print_result(result: CheckResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    line = f"[{status}] {result.label}"
    if result.detail:
        line = f"{line} - {result.detail}"
    print(line)


def main() -> int:
    add_project_root_to_path()
    print(f"Debug check root: {ROOT}")
    print()

    results: list[CheckResult] = []
    for label, check in iter_checks():
        result = run_check(label, check)
        results.append(result)
        print_result(result)

    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed
    print()
    print(f"Summary: {passed} PASS, {failed} FAIL")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
