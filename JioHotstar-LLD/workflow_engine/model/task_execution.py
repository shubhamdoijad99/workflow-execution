"""One attempt to run a task definition inside a workflow execution."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from workflow_engine.common import new_id
from workflow_engine.enums.execution_status import ExecutionStatus
from workflow_engine.model.task_definition import TaskDefinition


class TaskExecution:
    def __init__(self, task_definition: TaskDefinition) -> None:
        self.task_execution_id = new_id()
        self.task_definition = task_definition
        self.status = ExecutionStatus.PENDING
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.output: Any = None
        self.error: str | None = None

    def __repr__(self) -> str:
        return (
            f"TaskExecution(task_execution_id={self.task_execution_id!r}, "
            f"name={self.task_definition.name!r}, status={self.status.value})"
        )
