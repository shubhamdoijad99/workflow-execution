"""Storage port for workflow definitions."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod

from workflow_engine.exception.errors import DuplicateWorkflowError
from workflow_engine.model.workflow import Workflow


class WorkflowRepository(ABC):
    """Persistence port. Services depend on this, not on a storage technology."""

    @abstractmethod
    def add(self, workflow: Workflow) -> None:
        """Store a new workflow. Raise if the id already exists."""

    @abstractmethod
    def get(self, workflow_id: str) -> Workflow | None:
        """Return the workflow, or None when it is missing."""

    @abstractmethod
    def list_all(self) -> list[Workflow]:
        """Return workflows in insertion order."""


class InMemoryWorkflowRepository(WorkflowRepository):
    """Thread-safe in-memory workflow store."""

    def __init__(self) -> None:
        self._items: dict[str, Workflow] = {}
        self._lock = threading.Lock()

    def add(self, workflow: Workflow) -> None:
        with self._lock:
            if workflow.workflow_id in self._items:
                raise DuplicateWorkflowError(workflow.workflow_id)
            self._items[workflow.workflow_id] = workflow

    def get(self, workflow_id: str) -> Workflow | None:
        with self._lock:
            return self._items.get(workflow_id)

    def list_all(self) -> list[Workflow]:
        with self._lock:
            return list(self._items.values())
