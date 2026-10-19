"""Request and response bodies for execution resources."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from workflow_engine.enums.execution_status import ExecutionStatus
from workflow_engine.model.workflow_execution import WorkflowExecution


class ExecuteWorkflowResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    execution_id: str = Field(alias="executionId")
    workflow_id: str = Field(alias="workflowId")
    status: ExecutionStatus
    resume_at: Optional[str] = Field(default=None, alias="resumeAt")

    @classmethod
    def from_domain(cls, execution: WorkflowExecution) -> ExecuteWorkflowResponse:
        snap = execution.snapshot()
        return cls(
            execution_id=snap["execution_id"],
            workflow_id=snap["workflow_id"],
            status=snap["status"],
            resume_at=snap["resume_at"],
        )


class TaskExecutionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(alias="taskId")
    task_name: str = Field(alias="taskName")
    started_at: Optional[str] = Field(alias="startedAt")
    completed_at: Optional[str] = Field(alias="completedAt")
    metadata: dict[str, Any]
    status: ExecutionStatus


class ExecutionDetailResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    execution_id: str = Field(alias="executionId")
    workflow_id: str = Field(alias="workflowId")
    status: ExecutionStatus
    resume_at: Optional[str] = Field(default=None, alias="resumeAt")
    started_at: Optional[str] = Field(alias="startedAt")
    completed_at: Optional[str] = Field(alias="completedAt")
    error: Optional[str] = None
    tasks: list[TaskExecutionResponse]

    @classmethod
    def from_domain(cls, execution: WorkflowExecution) -> ExecutionDetailResponse:
        snap = execution.snapshot()
        return cls(
            execution_id=snap["execution_id"],
            workflow_id=snap["workflow_id"],
            status=snap["status"],
            resume_at=snap["resume_at"],
            started_at=snap["started_at"],
            completed_at=snap["completed_at"],
            error=snap["error"],
            tasks=[
                TaskExecutionResponse(
                    task_id=task["task_id"],
                    task_name=task["name"],
                    started_at=task["started_at"],
                    completed_at=task["completed_at"],
                    status=task["status"],
                    metadata={
                        "type": task["type"],
                        "config": task["config"],
                        "output": task["output"],
                        "error": task["error"],
                        "taskExecutionId": task["task_execution_id"],
                    },
                )
                for task in snap["tasks"]
            ],
        )


class ExecutionSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    execution_id: str = Field(alias="executionId")
    workflow_id: str = Field(alias="workflowId")
    status: ExecutionStatus
    resume_at: Optional[str] = Field(default=None, alias="resumeAt")

    @classmethod
    def from_domain(cls, execution: WorkflowExecution) -> ExecutionSummaryResponse:
        snap = execution.snapshot()
        return cls(
            execution_id=snap["execution_id"],
            workflow_id=snap["workflow_id"],
            status=snap["status"],
            resume_at=snap["resume_at"],
        )


class ExecutionListResponse(BaseModel):
    executions: list[ExecutionSummaryResponse]
