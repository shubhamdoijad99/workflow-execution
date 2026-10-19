"""One trigger of a workflow. Task runs stay on this execution only."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from workflow_engine.common import new_id, utcnow
from workflow_engine.enums.execution_status import ExecutionStatus
from workflow_engine.model.task_context import TaskContext
from workflow_engine.model.task_definition import TaskDefinition
from workflow_engine.model.task_execution import TaskExecution
from workflow_engine.model.workflow import Workflow


class WorkflowExecution:
    def __init__(
        self,
        workflow: Workflow,
        tasks: tuple[TaskDefinition, ...] | list[TaskDefinition],
        execution_id: str | None = None,
    ) -> None:
        self.execution_id = execution_id or new_id()
        self.workflow_id = workflow.workflow_id
        self.workflow_name = workflow.name
        self.status = ExecutionStatus.PENDING
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.resume_at: datetime | None = None
        self.error: str | None = None
        self._task_executions = tuple(TaskExecution(task) for task in tasks)
        self._done = threading.Event()
        self._lock = threading.Lock()

    @property
    def task_executions(self) -> tuple[TaskExecution, ...]:
        return self._task_executions

    def context_for(self, task_execution: TaskExecution) -> TaskContext:
        return TaskContext(
            workflow_id=self.workflow_id,
            execution_id=self.execution_id,
            task_execution_id=task_execution.task_execution_id,
        )

    def mark_running(self) -> None:
        with self._lock:
            self.status = ExecutionStatus.RUNNING
            self.resume_at = None
            if self.started_at is None:
                self.started_at = utcnow()

    def pause_for_task(
        self,
        task_execution: TaskExecution,
        output: Any,
        resume_at: datetime,
    ) -> None:
        """Release the worker. The sleep task stays in progress until ``resume_at``."""
        with self._lock:
            task_execution.output = output
            self.status = ExecutionStatus.WORKFLOW_PAUSED
            self.resume_at = resume_at

    def begin_task(self, task_execution: TaskExecution) -> None:
        with self._lock:
            task_execution.status = ExecutionStatus.RUNNING
            task_execution.started_at = utcnow()

    def complete_task(self, task_execution: TaskExecution, output: Any) -> None:
        with self._lock:
            task_execution.status = ExecutionStatus.COMPLETED
            task_execution.completed_at = utcnow()
            task_execution.output = output

    def fail_task(self, task_execution: TaskExecution, error: str) -> None:
        with self._lock:
            task_execution.status = ExecutionStatus.FAILED
            task_execution.completed_at = utcnow()
            task_execution.error = error

    def mark_completed(self) -> None:
        with self._lock:
            self.status = ExecutionStatus.COMPLETED
            self.completed_at = utcnow()
            self.resume_at = None

    def mark_failed(self, error: str) -> None:
        with self._lock:
            self.status = ExecutionStatus.FAILED
            self.completed_at = utcnow()
            self.error = error
            self.resume_at = None

    def signal_done(self) -> None:
        self._done.set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._done.wait(timeout)

    def snapshot(self) -> dict[str, Any]:
        """Consistent view of this execution, safe to read while it is running."""
        with self._lock:
            return {
                "execution_id": self.execution_id,
                "workflow_id": self.workflow_id,
                "workflow_name": self.workflow_name,
                "status": self.status.value,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "resume_at": self.resume_at.isoformat() if self.resume_at else None,
                "error": self.error,
                "tasks": [
                    {
                        "task_execution_id": task.task_execution_id,
                        "task_id": task.task_definition.task_id,
                        "name": task.task_definition.name,
                        "type": task.task_definition.task_type.value,
                        "config": dict(task.task_definition.config),
                        "status": task.status.value,
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                        "completed_at": (
                            task.completed_at.isoformat() if task.completed_at else None
                        ),
                        "output": task.output,
                        "error": task.error,
                    }
                    for task in self._task_executions
                ],
            }
