"""Definition of one ordered step in a workflow."""

from __future__ import annotations

from typing import Any

from workflow_engine.enums.task_type import TaskType


class TaskDefinition:
    """Immutable description of work. It does not store run state."""

    def __init__(
        self,
        task_id: str,
        name: str,
        task_type: TaskType,
        config: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(task_type, TaskType):
            raise ValueError(f"task_type must be a TaskType, got {task_type!r}")
        if not task_id or not str(task_id).strip():
            raise ValueError("task_id is required")
        if not name or not str(name).strip():
            raise ValueError("task name is required")
        self.task_id = str(task_id).strip()
        self.name = str(name).strip()
        self.task_type = task_type
        self.config = dict(config or {})

    def __repr__(self) -> str:
        return (
            f"TaskDefinition(task_id={self.task_id!r}, name={self.name!r}, "
            f"task_type={self.task_type.value})"
        )
