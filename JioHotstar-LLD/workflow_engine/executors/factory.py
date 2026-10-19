"""Resolves a TaskExecutor for a TaskType."""

from __future__ import annotations

from workflow_engine.enums.task_type import TaskType
from workflow_engine.exception.errors import TaskExecutionError
from workflow_engine.executors.base import TaskExecutor
from workflow_engine.executors.console_executor import ConsoleTaskExecutor
from workflow_engine.executors.http_executor import HttpTaskExecutor
from workflow_engine.executors.sleep_executor import SleepTaskExecutor


class TaskExecutorFactory:
    """Maps each task type to the strategy that knows how to run it."""

    def __init__(self) -> None:
        self._executors: dict[TaskType, TaskExecutor] = {
            TaskType.SLEEP: SleepTaskExecutor(),
            TaskType.CONSOLE: ConsoleTaskExecutor(),
            TaskType.HTTP: HttpTaskExecutor(),
        }

    def register(self, task_type: TaskType, executor: TaskExecutor) -> None:
        if not isinstance(task_type, TaskType):
            raise ValueError(f"task_type must be a TaskType, got {task_type!r}")
        if not isinstance(executor, TaskExecutor):
            raise TypeError("executor must implement TaskExecutor")
        self._executors[task_type] = executor

    def get(self, task_type: TaskType) -> TaskExecutor:
        executor = self._executors.get(task_type)
        if executor is None:
            label = task_type.value if isinstance(task_type, TaskType) else task_type
            raise TaskExecutionError(f"no executor registered for task type {label}")
        return executor
