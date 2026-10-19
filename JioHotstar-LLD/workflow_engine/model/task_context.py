"""Identity passed to an executor for the run it is inside."""


class TaskContext:
    def __init__(
        self,
        workflow_id: str,
        execution_id: str,
        task_execution_id: str,
    ) -> None:
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.task_execution_id = task_execution_id
