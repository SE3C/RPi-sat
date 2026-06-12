"""Team lead integration entrypoint for the CubeSat software project."""

from __future__ import annotations

from importlib import import_module
from time import perf_counter
import traceback
from typing import Any, Callable

try:
    import config
except Exception:
    config = None  # type: ignore[assignment]


TASKS: tuple[tuple[str, str, str], ...] = (
    ("GPS", "sensors.gps", "read_gps"),
    ("DHT11", "sensors.dht11", "read_dht11"),
    ("BMP280", "sensors.bmp280", "read_bmp280"),
    ("MPU6050", "sensors.mpu6050", "read_mpu6050"),
    ("BH1750", "sensors.bh1750", "read_bh1750"),
)

OUTPUT_TASKS: tuple[tuple[str, str, str], ...] = (
    ("LED_WAITING", "output.led", "show_waiting"),
    ("LED_OFF", "output.led", "all_off"),
    ("BUZZER_SHORT", "output.buzzer", "short_beep"),
)

STAGES: tuple[str, ...] = ("module_import", "callable_lookup", "execution")


def _config_value(name: str, default: Any) -> Any:
    if config is None:
        return default
    return getattr(config, name, default)


def _include_tracebacks() -> bool:
    return bool(_config_value("INTEGRATION_INCLUDE_TRACEBACKS", False))


def _error_result(name: str, message: str, stage: str | None = None) -> dict[str, Any]:
    return {
        "device": name,
        "ok": False,
        "status": "error",
        "stage": stage,
        "error": message,
    }


def _load_callable(module_name: str, function_name: str) -> Callable[[], Any]:
    module = import_module(module_name)
    candidate = getattr(module, function_name)
    if not callable(candidate):
        raise TypeError(f"{module_name}.{function_name} is not callable")
    return candidate


def _elapsed(started_at: float) -> float:
    return round(perf_counter() - started_at, 6)


def _stage_record(name: str, status: str, duration: float, error: str | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "stage": name,
        "status": status,
        "ok": status == "ok",
        "duration_seconds": duration,
    }
    if error:
        record["error"] = error
    return record


def _skip_remaining_stages(record: dict[str, Any]) -> None:
    finished = {stage["stage"] for stage in record["stages"]}
    for stage_name in STAGES:
        if stage_name not in finished:
            record["stages"].append(_stage_record(stage_name, "skipped", 0.0))


def _result_ok(result: Any) -> bool:
    if not isinstance(result, dict):
        return True

    if "ok" in result:
        return bool(result["ok"])

    status = result.get("status")
    if isinstance(status, str):
        normalized = status.lower()
        if normalized in {"ok", "success", "ready"}:
            return True
        if normalized in {"error", "failed", "fail", "unavailable"}:
            return False

    return not bool(result.get("error"))


def _result_error(result: Any) -> str | None:
    if not isinstance(result, dict):
        return None
    for key in ("error", "message", "reason"):
        value = result.get(key)
        if value:
            return str(value)
    errors = result.get("errors")
    if errors:
        return str(errors)
    return None


def _set_error(record: dict[str, Any], stage: str, exc: Exception) -> None:
    record["ok"] = False
    record["status"] = "error"
    record["error"] = str(exc)
    record["error_stage"] = stage
    if _include_tracebacks():
        record["traceback"] = traceback.format_exc()


def _run_integration_task(name: str, module_name: str, function_name: str) -> dict[str, Any]:
    total_started_at = perf_counter()
    target = f"{module_name}.{function_name}"
    record: dict[str, Any] = {
        "device": name,
        "target": target,
        "ok": False,
        "status": "error",
        "stages": [],
    }

    stage_started_at = perf_counter()
    try:
        module = import_module(module_name)
    except Exception as exc:
        duration = _elapsed(stage_started_at)
        record["stages"].append(_stage_record("module_import", "error", duration, str(exc)))
        _set_error(record, "module_import", exc)
        _skip_remaining_stages(record)
        record["duration_seconds"] = _elapsed(total_started_at)
        return record
    record["stages"].append(_stage_record("module_import", "ok", _elapsed(stage_started_at)))

    stage_started_at = perf_counter()
    try:
        candidate = getattr(module, function_name)
        if not callable(candidate):
            raise TypeError(f"{target} is not callable")
    except Exception as exc:
        duration = _elapsed(stage_started_at)
        record["stages"].append(_stage_record("callable_lookup", "error", duration, str(exc)))
        _set_error(record, "callable_lookup", exc)
        _skip_remaining_stages(record)
        record["duration_seconds"] = _elapsed(total_started_at)
        return record
    record["stages"].append(_stage_record("callable_lookup", "ok", _elapsed(stage_started_at)))

    stage_started_at = perf_counter()
    try:
        result = candidate()
    except Exception as exc:
        duration = _elapsed(stage_started_at)
        record["stages"].append(_stage_record("execution", "error", duration, str(exc)))
        _set_error(record, "execution", exc)
        record["result"] = _error_result(name, str(exc), "execution")
        record["duration_seconds"] = _elapsed(total_started_at)
        return record

    ok = _result_ok(result)
    result_error = _result_error(result)
    execution_status = "ok" if ok else "error"
    record["stages"].append(
        _stage_record(
            "execution",
            execution_status,
            _elapsed(stage_started_at),
            None if ok else result_error or "callable returned an error result",
        )
    )
    record["result"] = result
    record["ok"] = ok
    record["status"] = "ok" if ok else "error"
    if not ok:
        record["error"] = result_error or "callable returned an error result"
        record["error_stage"] = "execution"
    record["duration_seconds"] = _elapsed(total_started_at)
    return record


def run_sensor_checks() -> dict[str, Any]:
    results: dict[str, Any] = {}

    for name, module_name, function_name in TASKS:
        results[name] = _run_integration_task(name, module_name, function_name)

    return results


def run_output_self_test() -> dict[str, Any]:
    results: dict[str, Any] = {}

    for name, module_name, function_name in OUTPUT_TASKS:
        results[name] = _run_integration_task(name, module_name, function_name)

    return results


def _summary(results: dict[str, Any]) -> dict[str, Any]:
    total = len(results)
    ok_count = sum(1 for result in results.values() if result.get("ok") is True)
    duration = round(sum(result.get("duration_seconds", 0.0) for result in results.values()), 6)
    return {
        "total": total,
        "ok": ok_count,
        "error": total - ok_count,
        "duration_seconds": duration,
    }


def _preview(value: Any) -> str:
    limit = int(_config_value("INTEGRATION_RESULT_PREVIEW_CHARS", 240))
    text = repr(value)
    if len(text) > limit:
        return f"{text[:limit]}..."
    return text


def _print_results(title: str, results: dict[str, Any]) -> None:
    summary = _summary(results)
    print(
        f"{title}: {summary['ok']}/{summary['total']} ok, "
        f"{summary['error']} error, {summary['duration_seconds']:.3f}s total"
    )
    for name, result in results.items():
        print(
            f"- {name}: {result['status'].upper()} "
            f"{result.get('duration_seconds', 0.0):.3f}s target={result.get('target')}"
        )
        for stage in result.get("stages", []):
            line = (
                f"  - {stage['stage']}: {stage['status'].upper()} "
                f"{stage.get('duration_seconds', 0.0):.3f}s"
            )
            if stage.get("error"):
                line += f" error={stage['error']}"
            print(line)
        if result.get("ok"):
            print(f"  result={_preview(result.get('result'))}")
        else:
            print(
                f"  error_stage={result.get('error_stage', 'unknown')} "
                f"error={result.get('error', 'unknown error')}"
            )
            result_payload = result.get("result")
            if isinstance(result_payload, dict) and "debug" in result_payload:
                print(f"  debug={_preview(result_payload['debug'])}")
            elif result_payload is not None:
                print(f"  result={_preview(result_payload)}")


def main() -> None:
    print("CubeSat software integration check")

    sensor_results = run_sensor_checks()
    _print_results("Sensor results", sensor_results)

    output_results = run_output_self_test()
    _print_results("Output results", output_results)

    combined = {**sensor_results, **output_results}
    summary = _summary(combined)
    print(
        f"Overall summary: {summary['ok']}/{summary['total']} ok, "
        f"{summary['error']} error, {summary['duration_seconds']:.3f}s total"
    )


if __name__ == "__main__":
    main()
