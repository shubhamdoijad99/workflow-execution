"""Exercise the workflow HTTP API.

    python3 main.py           # run the API checks
    python3 main.py --serve   # start the server on 127.0.0.1:8000
"""

from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import combinations

from fastapi.testclient import TestClient

from workflow_engine.app import create_app, serve


class _DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/fail"):
            self._respond(500, b'{"ok": false}')
            return
        self._respond(200, b'{"ok": true}')

    def _respond(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _start_server() -> tuple[ThreadingHTTPServer, int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _DemoHandler)
    server.daemon_threads = True
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, name="demo-http", daemon=True)
    thread.start()
    return server, port


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  ok: {message}")


def _show(title: str, payload: object) -> None:
    print(f"\n{title}")
    print(json.dumps(payload, indent=2))


def _wait_for(client: TestClient, execution_id: str, timeout: float = 5) -> dict:
    deadline = time.monotonic() + timeout
    body: dict = {}
    while time.monotonic() < deadline:
        response = client.get(f"/executions/{execution_id}")
        response.raise_for_status()
        body = response.json()
        if body["status"] in {"COMPLETED", "FAILED"}:
            return body
        time.sleep(0.05)
    raise AssertionError(f"execution {execution_id} still {body.get('status')}")


def _parse(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def run_api_demo(port: int) -> None:
    sleep_seconds = 0.4
    app = create_app(max_workers=4)
    with TestClient(app) as client:
        health = client.get("/health")
        _check(health.status_code == 200 and health.json()["status"] == "ok", "GET /health")

        created = client.post(
            "/workflows",
            json={
                "name": "sample-workflow",
                "tasks": [
                    {
                        "type": "CONSOLE",
                        "name": "greet",
                        "config": {"message": "Workflow started"},
                    },
                    {
                        "type": "SLEEP",
                        "name": "pause",
                        "config": {"duration_seconds": sleep_seconds},
                    },
                    {
                        "type": "HTTP",
                        "name": "fetch",
                        "config": {
                            "url": f"http://127.0.0.1:{port}/ok",
                            "method": "GET",
                            "timeout": 5,
                        },
                    },
                    {
                        "type": "CONSOLE",
                        "name": "done",
                        "config": {"message": "Workflow finished"},
                    },
                ],
            },
        )
        _check(created.status_code == 201, "POST /workflows returns 201")
        created_body = created.json()
        _show("POST /workflows", created_body)
        _check("workflow_id" in created_body, "create response contains workflow_id")
        workflow_id = created_body["workflow_id"]

        listed = client.get("/workflows")
        _check(listed.status_code == 200, "GET /workflows")
        _check(
            any(item["workflow_id"] == workflow_id for item in listed.json()["workflows"]),
            "created workflow is listed",
        )
        definition = client.get(f"/workflows/{workflow_id}")
        _check(definition.status_code == 200, "GET /workflows/{workflow_id}")
        task_names = [task["name"] for task in definition.json()["tasks"]]
        _check(
            task_names == ["greet", "pause", "fetch", "done"],
            "tasks are stored in request order",
        )

        print("\n=== POST /workflows/{workflow_id}/execute x3 ===")
        started = time.perf_counter()
        execution_ids = []
        for _ in range(3):
            response = client.post(f"/workflows/{workflow_id}/execute")
            _check(response.status_code == 202, "execute returns 202")
            body = response.json()
            _check(
                {"executionId", "workflowId", "status"} <= set(body),
                "execute response has executionId, workflowId, and status",
            )
            _check(body["workflowId"] == workflow_id, "execute response points at the workflow")
            execution_ids.append(body["executionId"])
            _show("POST /workflows/{workflow_id}/execute", body)

        executions = [_wait_for(client, execution_id) for execution_id in execution_ids]
        elapsed = time.perf_counter() - started
        print(f"\n3 runs finished in {elapsed:.2f}s")
        _show("GET /executions/{executionId}", executions[0])

        _check(len(set(execution_ids)) == 3, "each trigger has its own execution id")
        for execution in executions:
            _check(execution["status"] == "COMPLETED", f"{execution['executionId']} completed")
            names = [task["taskName"] for task in execution["tasks"]]
            statuses = [task["status"] for task in execution["tasks"]]
            _check(names == ["greet", "pause", "fetch", "done"], "task names are returned in order")
            _check(statuses == ["COMPLETED"] * 4, "tasks ran in order and completed")
            for previous, current in zip(execution["tasks"], execution["tasks"][1:]):
                previous_done = _parse(previous["completedAt"])
                current_started = _parse(current["startedAt"])
                assert previous_done is not None and current_started is not None
                if current_started < previous_done:
                    raise AssertionError("a later task started before the previous task finished")
            fetch = execution["tasks"][2]
            _check(
                fetch["metadata"]["output"]["status_code"] == 200,
                "HTTP task metadata contains the response status",
            )
            _check(
                {"taskId", "taskName", "startedAt", "completedAt", "metadata", "status"}
                <= set(fetch),
                "task payload matches the execution contract",
            )

        pauses = []
        for execution in executions:
            pause = next(task for task in execution["tasks"] if task["taskName"] == "pause")
            pauses.append((_parse(pause["startedAt"]), _parse(pause["completedAt"])))
        _check(
            any(
                left[0] < right[1] and right[0] < left[1]
                for left, right in combinations(pauses, 2)
            ),
            "sleep tasks from separate executions overlapped",
        )
        _check(
            elapsed < 3 * sleep_seconds,
            f"wall clock {elapsed:.2f}s is below three sequential sleeps",
        )

        history = client.get(f"/workflows/{workflow_id}/executions")
        _check(history.status_code == 200, "GET /workflows/{workflow_id}/executions")
        _check(len(history.json()["executions"]) == 3, "three executions are tracked")

        print("\n=== failed task fails that execution only ===")
        failing = client.post(
            "/workflows",
            json={
                "name": "failing-pipeline",
                "tasks": [
                    {
                        "type": "CONSOLE",
                        "name": "before",
                        "config": {"message": "before failure"},
                    },
                    {
                        "type": "HTTP",
                        "name": "bad-call",
                        "config": {
                            "url": f"http://127.0.0.1:{port}/fail",
                            "method": "GET",
                            "timeout": 5,
                        },
                    },
                    {
                        "type": "CONSOLE",
                        "name": "after",
                        "config": {"message": "after failure — this must not print"},
                    },
                ],
            },
        )
        failing_id = failing.json()["workflow_id"]
        success = client.post(f"/workflows/{workflow_id}/execute")
        failure = client.post(f"/workflows/{failing_id}/execute")
        success_body = _wait_for(client, success.json()["executionId"])
        failure_body = _wait_for(client, failure.json()["executionId"])
        _show("GET failed execution", failure_body)
        _check(success_body["status"] == "COMPLETED", "sibling execution still completed")
        _check(failure_body["status"] == "FAILED", "failed task fails the workflow execution")
        _check(failure_body["tasks"][0]["status"] == "COMPLETED", "earlier task completed")
        _check(failure_body["tasks"][1]["status"] == "FAILED", "HTTP 500 fails the task")
        _check(failure_body["tasks"][2]["status"] == "PENDING", "later task stays pending")
        _check(failure_body["tasks"][2]["startedAt"] is None, "pending task has no startedAt")
        _check(
            "HTTP 500" in failure_body["tasks"][1]["metadata"]["error"],
            "failure metadata contains the HTTP error",
        )

        again = _wait_for(
            client,
            client.post(f"/workflows/{workflow_id}/execute").json()["executionId"],
        )
        _check(again["status"] == "COMPLETED", "a later trigger still runs after a failure")

        missing = client.get("/executions/does-not-exist")
        _check(missing.status_code == 404, "unknown execution returns 404")
        _check(missing.json()["error"] == "execution_not_found", "404 body names the error")

        invalid = client.post(
            "/workflows",
            json={
                "name": "bad-http",
                "tasks": [
                    {"type": "HTTP", "config": {"url": "", "method": "", "timeout": ""}}
                ],
            },
        )
        _check(invalid.status_code == 400, "empty HTTP url is rejected")
        _check(invalid.json()["error"] == "invalid_request", "invalid task config returns invalid_request")

        unknown_type = client.post(
            "/workflows",
            json={"name": "bad-type", "tasks": [{"type": "NOPE", "config": {}}]},
        )
        _check(unknown_type.status_code == 422, "unknown task type returns 422")

        added = client.post(
            f"/workflows/{workflow_id}/tasks",
            json={"type": "CONSOLE", "name": "extra", "config": {"message": "added later"}},
        )
        _check(added.status_code == 201, "POST /workflows/{workflow_id}/tasks returns 201")
        refreshed = client.get(f"/workflows/{workflow_id}")
        _check(
            refreshed.json()["tasks"][-1]["name"] == "extra",
            "added task is appended to the workflow",
        )

        all_executions = client.get("/executions")
        _check(all_executions.status_code == 200, "GET /executions")
        _check(
            len(all_executions.json()["executions"]) >= 3,
            "execution list includes the runs created above",
        )

        print("\nall checks passed")


def main() -> None:
    if "--serve" in sys.argv:
        serve()
        return
    server, port = _start_server()
    try:
        run_api_demo(port)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
