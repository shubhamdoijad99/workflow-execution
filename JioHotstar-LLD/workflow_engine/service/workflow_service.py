"""Create and read workflow definitions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from workflow_engine.common import new_id
from workflow_engine.enums.task_type import TaskType
from workflow_engine.exception.errors import InvalidRequestError, WorkflowNotFoundError
from workflow_engine.model.task_definition import TaskDefinition
from workflow_engine.model.workflow import Workflow
from workflow_engine.repository.workflow_repository import WorkflowRepository
from workflow_engine.service.task_config import normalize_task_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NewTask:
    """Task a caller wants added to a workflow."""

    task_type: TaskType
    config: dict[str, Any]
    name: str | None = None
    task_id: str | None = None


class WorkflowService:
    def __init__(self, workflow_repository: WorkflowRepository) -> None:
        self._workflows = workflow_repository

    def create_workflow(self, name: str, tasks: list[NewTask]) -> Workflow:
        workflow = Workflow(new_id(), _require_name(name))
        for index, task in enumerate(tasks, start=1):
            workflow.add_task(self._to_definition(task, index))
        self._workflows.add(workflow)
        logger.info(
            "created workflow %s name=%s tasks=%s",
            workflow.workflow_id,
            workflow.name,
            len(tasks),
        )
        return workflow

    def add_task(self, workflow_id: str, task: NewTask) -> TaskDefinition:
        workflow = self.get_workflow(workflow_id)
        index = len(workflow.snapshot_tasks()) + 1
        definition = self._to_definition(task, index)
        workflow.add_task(definition)
        logger.info(
            "added task %s to workflow %s",
            definition.task_id,
            workflow.workflow_id,
        )
        return definition

    def get_workflow(self, workflow_id: str) -> Workflow:
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(workflow_id)
        return workflow

    def list_workflows(self) -> list[Workflow]:
        return self._workflows.list_all()

    def _to_definition(self, task: NewTask, index: int) -> TaskDefinition:
        name = task.name.strip() if task.name and task.name.strip() else None
        if name is None:
            name = f"{task.task_type.value.lower()}-{index}"
        task_id = task.task_id.strip() if task.task_id and task.task_id.strip() else new_id()
        return TaskDefinition(
            task_id=task_id,
            name=name,
            task_type=task.task_type,
            config=normalize_task_config(task.task_type, task.config),
        )


def _require_name(name: str) -> str:
    if not name or not str(name).strip():
        raise InvalidRequestError("workflow name is required")
    return str(name).strip()
