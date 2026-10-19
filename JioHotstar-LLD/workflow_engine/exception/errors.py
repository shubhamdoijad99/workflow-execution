"""Errors that cross the service boundary and map to API responses."""


class WorkflowEngineError(Exception):
    """Base class for errors the API turns into a JSON body."""

    status_code = 500
    code = "engine_error"


class InvalidRequestError(WorkflowEngineError):
    """The caller sent a workflow or task the engine will not store."""

    status_code = 400
    code = "invalid_request"


class WorkflowNotFoundError(WorkflowEngineError):
    """No workflow is stored under this id."""

    status_code = 404
    code = "workflow_not_found"

    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id
        super().__init__(f"workflow not found: {workflow_id}")


class DuplicateWorkflowError(WorkflowEngineError):
    """A workflow with this id is already stored."""

    status_code = 409
    code = "duplicate_workflow"

    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id
        super().__init__(f"workflow already exists: {workflow_id}")


class DuplicateTaskError(WorkflowEngineError):
    """A task id is already present on the workflow."""

    status_code = 409
    code = "duplicate_task"

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"task already exists: {task_id}")


class ExecutionNotFoundError(WorkflowEngineError):
    """No execution is stored under this id."""

    status_code = 404
    code = "execution_not_found"

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        super().__init__(f"execution not found: {execution_id}")


class EngineUnavailableError(WorkflowEngineError):
    """The engine is not accepting new executions."""

    status_code = 503
    code = "engine_unavailable"

    def __init__(self, message: str = "engine is shut down") -> None:
        super().__init__(message)


class TaskExecutionError(Exception):
    """A task failed while running. The execution service records it."""
