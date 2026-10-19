"""Console task strategy."""

from __future__ import annotations

import sys
from typing import Any, TextIO

from workflow_engine.exception.errors import TaskExecutionError
from workflow_engine.executors.base import TaskExecutor
from workflow_engine.model.task_context import TaskContext
from workflow_engine.model.task_definition import TaskDefinition


class ConsoleTaskExecutor(TaskExecutor):
    """Print ``config['message']`` to a stream."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdout

    def execute(self, task: TaskDefinition, context: TaskContext) -> Any:
        if "message" not in task.config:
            raise TaskExecutionError("CONSOLE task requires config 'message'")
        message = str(task.config["message"])
        short_id = context.execution_id[:8]
        print(
            f"[{short_id}] {task.name}: {message}",
            file=self._stream,
            flush=True,
        )
        return {
            "execution_id": context.execution_id,
            "message": message,
        }
