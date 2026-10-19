"""HTTP adapter for starting and reading workflow executions."""

from fastapi import APIRouter

from workflow_engine.dto.execution_dto import (
    ExecuteWorkflowResponse,
    ExecutionDetailResponse,
    ExecutionListResponse,
    ExecutionSummaryResponse,
)
from workflow_engine.service.execution_service import ExecutionService


class ExecutionController:
    def __init__(self, execution_service: ExecutionService) -> None:
        self._service = execution_service

    def execute(self, workflow_id: str) -> ExecuteWorkflowResponse:
        return ExecuteWorkflowResponse.from_domain(self._service.execute(workflow_id))

    def get_execution(self, execution_id: str) -> ExecutionDetailResponse:
        return ExecutionDetailResponse.from_domain(self._service.get_execution(execution_id))

    def list_for_workflow(self, workflow_id: str) -> ExecutionListResponse:
        return _list(self._service.list_executions(workflow_id))

    def list_executions(self) -> ExecutionListResponse:
        return _list(self._service.list_executions())


def build_execution_router(execution_service: ExecutionService) -> APIRouter:
    controller = ExecutionController(execution_service)
    router = APIRouter(tags=["executions"])

    @router.post(
        "/workflows/{workflow_id}/execute",
        status_code=202,
        response_model=ExecuteWorkflowResponse,
        response_model_by_alias=True,
    )
    def execute_workflow(workflow_id: str) -> ExecuteWorkflowResponse:
        """Queue a new run of a workflow. The same workflow can run many times."""
        return controller.execute(workflow_id)

    @router.get(
        "/workflows/{workflow_id}/executions",
        response_model=ExecutionListResponse,
        response_model_by_alias=True,
    )
    def list_workflow_executions(workflow_id: str) -> ExecutionListResponse:
        """List every trigger of one workflow."""
        return controller.list_for_workflow(workflow_id)

    @router.get(
        "/executions",
        response_model=ExecutionListResponse,
        response_model_by_alias=True,
    )
    def list_executions() -> ExecutionListResponse:
        """List executions across workflows."""
        return controller.list_executions()

    @router.get(
        "/executions/{execution_id}",
        response_model=ExecutionDetailResponse,
        response_model_by_alias=True,
    )
    def get_execution(execution_id: str) -> ExecutionDetailResponse:
        """Return the status of one run and of each task inside it."""
        return controller.get_execution(execution_id)

    return router


def _list(executions) -> ExecutionListResponse:
    return ExecutionListResponse(
        executions=[ExecutionSummaryResponse.from_domain(execution) for execution in executions]
    )
