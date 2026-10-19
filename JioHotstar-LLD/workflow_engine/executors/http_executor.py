"""HTTP task strategy."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from workflow_engine.exception.errors import TaskExecutionError
from workflow_engine.executors.base import TaskExecutor
from workflow_engine.model.task_context import TaskContext
from workflow_engine.model.task_definition import TaskDefinition

_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}
_MAX_BODY_CHARS = 1024


class HttpTaskExecutor(TaskExecutor):
    """Perform an HTTP call. Responses with status >= 400 fail the task."""

    def execute(self, task: TaskDefinition, context: TaskContext) -> Any:
        url = task.config.get("url")
        if not isinstance(url, str) or not url.strip():
            raise TaskExecutionError("HTTP task requires config 'url'")

        method = str(task.config.get("method", "GET")).upper()
        if method not in _ALLOWED_METHODS:
            raise TaskExecutionError(f"unsupported HTTP method: {method}")

        timeout = task.config.get("timeout_seconds", task.config.get("timeout", 10))
        if timeout in ("", None):
            timeout = 10
        if isinstance(timeout, str):
            try:
                timeout = float(timeout)
            except ValueError as exc:
                raise TaskExecutionError("timeout must be a positive number") from exc
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise TaskExecutionError("timeout must be a positive number")

        raw_headers = task.config.get("headers") or {}
        if not isinstance(raw_headers, dict):
            raise TaskExecutionError("headers must be a dict")
        headers = {str(key): str(value) for key, value in raw_headers.items()}
        headers.setdefault("User-Agent", "workflow-engine/1.0")

        data = _encode_body(task.config.get("body"), headers)
        request = urllib.request.Request(
            url.strip(),
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=float(timeout)) as response:
                status = int(response.status)
                body = response.read(_MAX_BODY_CHARS).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            exc.close()
            raise TaskExecutionError(
                f"HTTP {exc.code} from {method} {url}"
            ) from exc
        except urllib.error.URLError as exc:
            raise TaskExecutionError(
                f"HTTP request failed for {method} {url}: {exc.reason}"
            ) from exc

        if status >= 400:
            raise TaskExecutionError(f"HTTP {status} from {method} {url}")

        return {
            "execution_id": context.execution_id,
            "url": url,
            "method": method,
            "status_code": status,
            "body": body,
        }


def _encode_body(body: Any, headers: dict[str, str]) -> bytes | None:
    if body is None:
        return None
    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        return body.encode("utf-8")
    if isinstance(body, (dict, list)):
        headers.setdefault("Content-Type", "application/json")
        return json.dumps(body).encode("utf-8")
    raise TaskExecutionError("HTTP body must be a string, bytes, dict, list, or null")
