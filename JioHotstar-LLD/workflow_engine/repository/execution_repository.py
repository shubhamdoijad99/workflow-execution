"""Storage port for workflow executions."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod

from workflow_engine.model.workflow_execution import WorkflowExecution


class ExecutionRepository(ABC):
    """Persistence port for workflow runs."""

    @abstractmethod
    def add(self, execution: WorkflowExecution) -> None:
        """Store a new execution."""

    @abstractmethod
    def save(self, execution: WorkflowExecution) -> None:
        """Persist the current state of an execution."""

    @abstractmethod
    def get(self, execution_id: str) -> WorkflowExecution | None:
        """Return the execution, or None when it is missing."""

    @abstractmethod
    def list_all(self) -> list[WorkflowExecution]:
        """Return executions in insertion order."""

    @abstractmethod
    def list_by_workflow(self, workflow_id: str) -> list[WorkflowExecution]:
        """Return executions that were triggered from one workflow."""


class InMemoryExecutionRepository(ExecutionRepository):
    """Thread-safe in-memory execution store.

    The repository keeps the live aggregate. ``save`` writes that same object
    back so a later database-backed repository can persist each transition.
    """

    def __init__(self) -> None:
        self._items: dict[str, WorkflowExecution] = {}
        self._lock = threading.Lock()

    def add(self, execution: WorkflowExecution) -> None:
        self.save(execution)

    def save(self, execution: WorkflowExecution) -> None:
        with self._lock:
            self._items[execution.execution_id] = execution

    def get(self, execution_id: str) -> WorkflowExecution | None:
        with self._lock:
            return self._items.get(execution_id)

    def list_all(self) -> list[WorkflowExecution]:
        with self._lock:
            return list(self._items.values())

    def list_by_workflow(self, workflow_id: str) -> list[WorkflowExecution]:
        with self._lock:
            return [
                execution
                for execution in self._items.values()
                if execution.workflow_id == workflow_id
            ]
