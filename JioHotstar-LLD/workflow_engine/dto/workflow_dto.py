"""Request and response bodies for workflow resources."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from workflow_engine.enums.task_type import TaskType
from workflow_engine.model.task_definition import TaskDefinition
from workflow_engine.model.workflow import Workflow


class CreateTaskRequest(BaseModel):
    """One task inside a create-workflow or add-task call."""

    type: TaskType
    config: dict[str, Any] = Field(default_factory=dict)
    name: Optional[str] = None
    task_id: Optional[str] = None


class CreateWorkflowRequest(BaseModel):
    name: str = Field(min_length=1)
    tasks: list[CreateTaskRequest] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "sample-workflow",
                "tasks": [
                    {
                        "type": "CONSOLE",
                        "config": {"message": "Workflow started"},
                    },
                    {
                        "type": "HTTP",
                        "config": {
                            "url": "https://example.com",
                            "method": "GET",
                            "timeout": 5,
                        },
                    },
                ],
            }
        }
    )


class CreateWorkflowResponse(BaseModel):
    workflow_id: str


class TaskDefinitionResponse(BaseModel):
    task_id: str
    name: str
    type: TaskType
    config: dict[str, Any]

    @classmethod
    def from_domain(cls, task: TaskDefinition) -> TaskDefinitionResponse:
        return cls(
            task_id=task.task_id,
            name=task.name,
            type=task.task_type,
            config=dict(task.config),
        )


class WorkflowResponse(BaseModel):
    workflow_id: str
    name: str
    tasks: list[TaskDefinitionResponse]

    @classmethod
    def from_domain(cls, workflow: Workflow) -> WorkflowResponse:
        return cls(
            workflow_id=workflow.workflow_id,
            name=workflow.name,
            tasks=[
                TaskDefinitionResponse.from_domain(task)
                for task in workflow.snapshot_tasks()
            ],
        )


class WorkflowListResponse(BaseModel):
    workflows: list[WorkflowResponse]
