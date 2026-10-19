"""Process settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    max_workers: int = 8


def load_settings() -> Settings:
    return Settings(
        host=os.getenv("WORKFLOW_HOST", "127.0.0.1"),
        port=int(os.getenv("WORKFLOW_PORT", "8000")),
        max_workers=int(os.getenv("WORKFLOW_MAX_WORKERS", "8")),
    )
