"""Trigger workflows and run their tasks."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

from workflow_engine.enums.execution_status import ExecutionStatus
from workflow_engine.exception.errors import (
    EngineUnavailableError,
    ExecutionNotFoundError,
    WorkflowNotFoundError,
)
from workflow_engine.executors.base import PauseTask
from workflow_engine.executors.factory import TaskExecutorFactory
from workflow_engine.model.task_execution import TaskExecution
from workflow_engine.model.workflow_execution import WorkflowExecution
from workflow_engine.repository.execution_repository import ExecutionRepository
from workflow_engine.repository.workflow_repository import WorkflowRepository
from workflow_engine.service.resume_scheduler import ResumeScheduler

logger = logging.getLogger(__name__)


class _Step(str, Enum):
    DONE = "DONE"
    PAUSED = "PAUSED"
    FAILED = "FAILED"


class ExecutionService:
    """Runs each execution on a worker. Tasks inside one execution stay ordered.

    A sleep task pauses the execution and returns the worker immediately.
    ``ResumeScheduler`` continues that execution at ``now + duration``.
    """

    def __init__(
        self,
        workflow_repository: WorkflowRepository,
        execution_repository: ExecutionRepository,
        executor_factory: TaskExecutorFactory | None = None,
        max_workers: int = 8,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        self._workflows = workflow_repository
        self._executions = execution_repository
        self._factory = executor_factory or TaskExecutorFactory()
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="workflow",
        )
        self._lock = threading.Lock()
        self._advance_locks: dict[str, threading.Lock] = {}
        self._accepting = True
        self._scheduler = ResumeScheduler(self._submit_resume)

    def execute(self, workflow_id: str) -> WorkflowExecution:
        """Queue a new run and return it while tasks are still in progress."""
        self._ensure_accepting()
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(workflow_id)

        execution = WorkflowExecution(workflow, workflow.snapshot_tasks())
        self._ensure_accepting()
        self._executions.add(execution)
        try:
            self._pool.submit(self._advance, execution)
        except RuntimeError as exc:
            execution.mark_failed("engine is shut down")
            execution.signal_done()
            self._executions.save(execution)
            raise EngineUnavailableError() from exc
        logger.info(
            "queued execution %s for workflow %s",
            execution.execution_id,
            workflow_id,
        )
        return execution

    def get_execution(self, execution_id: str) -> WorkflowExecution:
        execution = self._executions.get(execution_id)
        if execution is None:
            raise ExecutionNotFoundError(execution_id)
        return execution

    def list_executions(self, workflow_id: str | None = None) -> list[WorkflowExecution]:
        if workflow_id is None:
            return self._executions.list_all()
        if self._workflows.get(workflow_id) is None:
            raise WorkflowNotFoundError(workflow_id)
        return self._executions.list_by_workflow(workflow_id)

    def shutdown(self) -> None:
        with self._lock:
            self._accepting = False
        self._scheduler.close()
        self._pool.shutdown(wait=True)

    def _ensure_accepting(self) -> None:
        with self._lock:
            if not self._accepting:
                raise EngineUnavailableError()

    def _submit_resume(self, execution_id: str) -> None:
        try:
            self._pool.submit(self._resume, execution_id)
        except RuntimeError:
            logger.warning(
                "could not resume %s because the engine is shut down",
                execution_id,
            )

    def _resume(self, execution_id: str) -> None:
        execution = self._executions.get(execution_id)
        if execution is None:
            return
        with self._advance_lock(execution_id):
            if execution.status is not ExecutionStatus.WORKFLOW_PAUSED:
                return
            for task_execution in execution.task_executions:
                if task_execution.status is ExecutionStatus.RUNNING:
                    execution.complete_task(task_execution, task_execution.output)
                    break
            self._advance_locked(execution)

    def _advance(self, execution: WorkflowExecution) -> None:
        with self._advance_lock(execution.execution_id):
            self._advance_locked(execution)

    def _advance_locked(self, execution: WorkflowExecution) -> None:
        try:
            execution.mark_running()
            self._executions.save(execution)
            for task_execution in execution.task_executions:
                if task_execution.status is ExecutionStatus.COMPLETED:
                    continue
                step = self._run_task(execution, task_execution)
                if step is _Step.PAUSED:
                    return
                if step is _Step.FAILED:
                    execution.signal_done()
                    return
            execution.mark_completed()
            self._executions.save(execution)
            execution.signal_done()
            logger.info("execution %s completed", execution.execution_id)
        except Exception as exc:
            execution.mark_failed(f"Unexpected failure: {exc}")
            self._executions.save(execution)
            execution.signal_done()
            logger.exception("execution %s failed unexpectedly", execution.execution_id)

    def _advance_lock(self, execution_id: str) -> threading.Lock:
        with self._lock:
            lock = self._advance_locks.get(execution_id)
            if lock is None:
                lock = threading.Lock()
                self._advance_locks[execution_id] = lock
            return lock

    def _run_task(
        self,
        execution: WorkflowExecution,
        task_execution: TaskExecution,
    ) -> _Step:
        execution.begin_task(task_execution)
        self._executions.save(execution)
        task = task_execution.task_definition
        try:
            executor = self._factory.get(task.task_type)
            output = executor.execute(task, execution.context_for(task_execution))
        except Exception as exc:
            self._fail_workflow(execution, task_execution, str(exc))
            return _Step.FAILED
        if isinstance(output, PauseTask):
            execution.pause_for_task(task_execution, output.output, output.resume_at)
            self._executions.save(execution)
            self._scheduler.schedule(output.resume_at, execution.execution_id)
            logger.info(
                "paused execution %s until %s",
                execution.execution_id,
                output.resume_at.isoformat(),
            )
            return _Step.PAUSED
        execution.complete_task(task_execution, output)
        self._executions.save(execution)
        return _Step.DONE

    def _fail_workflow(
        self,
        execution: WorkflowExecution,
        task_execution: TaskExecution,
        error: str,
    ) -> None:
        """A failed task fails this execution and leaves later tasks pending."""
        execution.fail_task(task_execution, error)
        task_name = task_execution.task_definition.name
        execution.mark_failed(f"Task '{task_name}' failed: {error}")
        self._executions.save(execution)
        logger.warning(
            "execution %s failed on task %s: %s",
            execution.execution_id,
            task_name,
            error,
        )
