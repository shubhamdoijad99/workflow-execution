"""Task kinds a workflow definition can contain."""

from enum import Enum


class TaskType(str, Enum):
    """Work a task definition asks an executor to perform."""

    SLEEP = "SLEEP"
    CONSOLE = "CONSOLE"
    HTTP = "HTTP"
