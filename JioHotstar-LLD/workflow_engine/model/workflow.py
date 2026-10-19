"""Ordered workflow definition that can be triggered many times."""

from __future__ import annotations

import threading

from workflow_engine.common import utcnow
from workflow_engine.exception.errors import DuplicateTaskError
from workflow_engine.model.task_definition import TaskDefinition


class Workflow:
    def __init__(self, workflow_id: str, name: str) -> None:
        if not workflow_id or not str(workflow_id).strip():
            raise ValueError("workflow_id is required")
        if not name or not str(name).strip():
            raise ValueError("workflow name is required")
        self.workflow_id = str(workflow_id).strip()
        self.name = str(name).strip()
        self.created_at = utcnow()
        self._tasks: list[TaskDefinition] = []
        self._lock = threading.Lock()

    def add_task(self, task: TaskDefinition) -> None:
        with self._lock:
            if any(existing.task_id == task.task_id for existing in self._tasks):
                raise DuplicateTaskError(task.task_id)
            self._tasks.append(task)

    def snapshot_tasks(self) -> tuple[TaskDefinition, ...]:
        """Task order captured for one execution. Later adds are not included."""
        with self._lock:
            return tuple(self._tasks)

    def __repr__(self) -> str:
        return f"Workflow(workflow_id={self.workflow_id!r}, name={self.name!r})"
