"""Composition root. Wires repositories, services, and executors."""

from workflow_engine.executors.factory import TaskExecutorFactory
from workflow_engine.repository.execution_repository import InMemoryExecutionRepository
from workflow_engine.repository.workflow_repository import InMemoryWorkflowRepository
from workflow_engine.service.execution_service import ExecutionService
from workflow_engine.service.workflow_service import WorkflowService


class Container:
    def __init__(self, max_workers: int = 8) -> None:
        workflow_repository = InMemoryWorkflowRepository()
        execution_repository = InMemoryExecutionRepository()
        self.workflow_service = WorkflowService(workflow_repository)
        self.execution_service = ExecutionService(
            workflow_repository,
            execution_repository,
            TaskExecutorFactory(),
            max_workers=max_workers,
        )
