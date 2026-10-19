"""Lifecycle of a workflow run and of each task inside that run."""

from enum import Enum


class ExecutionStatus(str, Enum):
    """State of one workflow execution or one task execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WORKFLOW_PAUSED = "WORKFLOW_PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
