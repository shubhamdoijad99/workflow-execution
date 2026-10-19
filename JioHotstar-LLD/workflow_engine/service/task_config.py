"""Normalize and check task config before a workflow is stored."""

from __future__ import annotations

from typing import Any

from workflow_engine.enums.task_type import TaskType
from workflow_engine.exception.errors import InvalidRequestError

_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}


def normalize_task_config(task_type: TaskType, config: dict[str, Any] | None) -> dict[str, Any]:
    """Return a config dict the executor can run. Raise when it is not valid."""
    raw = dict(config or {})
    if task_type is TaskType.CONSOLE:
        return _console_config(raw)
    if task_type is TaskType.SLEEP:
        return _sleep_config(raw)
    if task_type is TaskType.HTTP:
        return _http_config(raw)
    raise InvalidRequestError(f"unsupported task type: {task_type}")


def _console_config(config: dict[str, Any]) -> dict[str, Any]:
    if "message" not in config:
        raise InvalidRequestError("CONSOLE task requires config.message")
    config["message"] = str(config["message"])
    return config


def _sleep_config(config: dict[str, Any]) -> dict[str, Any]:
    if "duration_seconds" not in config:
        raise InvalidRequestError("SLEEP task requires config.duration_seconds")
    config["duration_seconds"] = _as_number(
        "duration_seconds",
        config["duration_seconds"],
        minimum=0,
    )
    return config


def _http_config(config: dict[str, Any]) -> dict[str, Any]:
    url = config.get("url")
    if not isinstance(url, str) or not url.strip():
        raise InvalidRequestError("HTTP task requires config.url")
    config["url"] = url.strip()

    method = config.get("method")
    if method in (None, ""):
        config["method"] = "GET"
    else:
        normalized = str(method).upper()
        if normalized not in _HTTP_METHODS:
            raise InvalidRequestError(f"unsupported HTTP method: {method}")
        config["method"] = normalized

    timeout = config.pop("timeout", None)
    if timeout not in (None, ""):
        config["timeout_seconds"] = _as_number("timeout", timeout, minimum=0, positive=True)
    elif "timeout_seconds" in config:
        config["timeout_seconds"] = _as_number(
            "timeout_seconds",
            config["timeout_seconds"],
            positive=True,
        )
    return config


def _as_number(
    field: str,
    value: Any,
    minimum: float = 0,
    positive: bool = False,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise InvalidRequestError(f"{field} must be a number")
    try:
        number = float(value)
    except ValueError as exc:
        raise InvalidRequestError(f"{field} must be a number") from exc
    if positive and number <= 0:
        raise InvalidRequestError(f"{field} must be greater than 0")
    if number < minimum:
        raise InvalidRequestError(f"{field} must be >= {minimum}")
    return number
