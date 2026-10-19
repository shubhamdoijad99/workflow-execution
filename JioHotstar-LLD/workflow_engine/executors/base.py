"""Strategy interface for running a single task."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from workflow_engine.model.task_context import TaskContext
from workflow_engine.model.task_definition import TaskDefinition


class PauseTask:
    """Ask the engine to release the worker and continue at ``resume_at``.

    The worker must not block until then. The execution status becomes
    ``WORKFLOW_PAUSED`` and the scheduler resumes it.
    """

    def __init__(self, resume_at: datetime, output: dict[str, Any]) -> None:
        self.resume_at = resume_at
        self.output = output


class TaskExecutor(ABC):
    """Runs one task type. Implementations do not advance the workflow."""

    @abstractmethod
    def execute(self, task: TaskDefinition, context: TaskContext) -> Any:
        """Run ``task`` and return its output. Raise to signal failure.

        Return ``PauseTask`` to pause the workflow without blocking a worker.
        """
