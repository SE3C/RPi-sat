"""Team lead integration entrypoint for the CubeSat software project."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable


TASKS: tuple[tuple[str, str, str], ...] = (
    ("GPS", "sensors.gps", "read_gps"),
    ("DHT11", "sensors.dht11", "read_dht11"),
    ("BMP280", "sensors.bmp280", "read_bmp280"),
    ("MPU6050", "sensors.mpu6050", "read_mpu6050"),
    ("BH1750", "sensors.bh1750", "read_bh1750"),
)


def _error_result(name: str, message: str) -> dict[str, Any]:
    return {
        "device": name,
        "ok": False,
        "status": "error",
        "error": message,
    }


def _load_callable(module_name: str, function_name: str) -> Callable[[], Any]:
    module = import_module(module_name)
    candidate = getattr(module, function_name)
    if not callable(candidate):
        raise TypeError(f"{module_name}.{function_name} is not callable")
    return candidate


def run_sensor_checks() -> dict[str, Any]:
    results: dict[str, Any] = {}

    for name, module_name, function_name in TASKS:
        try:
            reader = _load_callable(module_name, function_name)
            results[name] = reader()
        except Exception as exc:
            results[name] = _error_result(name, str(exc))

    return results


def run_output_self_test() -> dict[str, Any]:
    results: dict[str, Any] = {}

    try:
        led = import_module("output.led")
        if hasattr(led, "show_waiting"):
            results["LED_WAITING"] = led.show_waiting()
        if hasattr(led, "all_off"):
            results["LED_OFF"] = led.all_off()
    except Exception as exc:
        results["LED"] = _error_result("LED", str(exc))

    try:
        buzzer = import_module("output.buzzer")
        if hasattr(buzzer, "short_beep"):
            results["BUZZER_SHORT"] = buzzer.short_beep()
    except Exception as exc:
        results["BUZZER"] = _error_result("BUZZER", str(exc))

    return results


def main() -> None:
    print("CubeSat software integration check")
    print("Sensor results:")
    for name, result in run_sensor_checks().items():
        print(f"- {name}: {result}")

    print("Output results:")
    for name, result in run_output_self_test().items():
        print(f"- {name}: {result}")


if __name__ == "__main__":
    main()

