"""Sleep task strategy. Computes a resume time and does not block the worker."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from workflow_engine.common import utcnow
from workflow_engine.exception.errors import TaskExecutionError
from workflow_engine.executors.base import PauseTask, TaskExecutor
from workflow_engine.model.task_context import TaskContext
from workflow_engine.model.task_definition import TaskDefinition


class SleepTaskExecutor(TaskExecutor):
    """Pause the workflow until ``now + duration_seconds``."""

    def execute(self, task: TaskDefinition, context: TaskContext) -> Any:
        duration = task.config.get("duration_seconds")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise TaskExecutionError(
                "SLEEP task requires numeric config 'duration_seconds'"
            )
        if duration < 0:
            raise TaskExecutionError("duration_seconds must be >= 0")
        paused_at = utcnow()
        resume_at = paused_at + timedelta(seconds=float(duration))
        return PauseTask(
            resume_at=resume_at,
            output={
                "execution_id": context.execution_id,
                "duration_seconds": float(duration),
                "paused_at": paused_at.isoformat(),
                "resume_at": resume_at.isoformat(),
            },
        )

