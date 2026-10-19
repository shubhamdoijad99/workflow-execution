"""HTTP adapter for workflow definitions."""

from fastapi import APIRouter

from workflow_engine.dto.workflow_dto import (
    CreateTaskRequest,
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    TaskDefinitionResponse,
    WorkflowListResponse,
    WorkflowResponse,
)
from workflow_engine.service.workflow_service import NewTask, WorkflowService


class WorkflowController:
    def __init__(self, workflow_service: WorkflowService) -> None:
        self._service = workflow_service

    def create(self, body: CreateWorkflowRequest) -> CreateWorkflowResponse:
        workflow = self._service.create_workflow(body.name, [_new_task(task) for task in body.tasks])
        return CreateWorkflowResponse(workflow_id=workflow.workflow_id)

    def list_workflows(self) -> WorkflowListResponse:
        return WorkflowListResponse(
            workflows=[
                WorkflowResponse.from_domain(workflow)
                for workflow in self._service.list_workflows()
            ]
        )

    def get_workflow(self, workflow_id: str) -> WorkflowResponse:
        return WorkflowResponse.from_domain(self._service.get_workflow(workflow_id))

    def add_task(self, workflow_id: str, body: CreateTaskRequest) -> TaskDefinitionResponse:
        task = self._service.add_task(workflow_id, _new_task(body))
        return TaskDefinitionResponse.from_domain(task)


def build_workflow_router(workflow_service: WorkflowService) -> APIRouter:
    controller = WorkflowController(workflow_service)
    router = APIRouter(prefix="/workflows", tags=["workflows"])

    @router.post("", status_code=201, response_model=CreateWorkflowResponse)
    def create_workflow(body: CreateWorkflowRequest) -> CreateWorkflowResponse:
        """Store a workflow and its ordered tasks."""
        return controller.create(body)

    @router.get("", response_model=WorkflowListResponse)
    def list_workflows() -> WorkflowListResponse:
        """List stored workflow definitions."""
        return controller.list_workflows()

    @router.get("/{workflow_id}", response_model=WorkflowResponse)
    def get_workflow(workflow_id: str) -> WorkflowResponse:
        """Return one workflow and its tasks in execution order."""
        return controller.get_workflow(workflow_id)

    @router.post(
        "/{workflow_id}/tasks",
        status_code=201,
        response_model=TaskDefinitionResponse,
    )
    def add_task(workflow_id: str, body: CreateTaskRequest) -> TaskDefinitionResponse:
        """Append a task. Runs already in progress keep their original task list."""
        return controller.add_task(workflow_id, body)

    return router


def _new_task(task: CreateTaskRequest) -> NewTask:
    return NewTask(
        task_type=task.type,
        config=dict(task.config),
        name=task.name,
        task_id=task.task_id,
    )
