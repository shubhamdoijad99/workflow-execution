"""FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from workflow_engine.config import load_settings
from workflow_engine.container import Container
from workflow_engine.controller.exception_handler import register_exception_handlers
from workflow_engine.controller.execution_controller import build_execution_router
from workflow_engine.controller.health_controller import build_health_router
from workflow_engine.controller.workflow_controller import build_workflow_router

logger = logging.getLogger(__name__)


def create_app(max_workers: int | None = None) -> FastAPI:
    """Build the HTTP application and its in-memory dependencies."""
    _configure_logging()
    settings = load_settings()
    container = Container(max_workers=max_workers or settings.max_workers)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info("workflow engine started")
        yield
        container.execution_service.shutdown()
        logger.info("workflow engine stopped")

    app = FastAPI(
        title="Workflow Engine",
        version="1.0.0",
        summary="In-memory workflow execution API",
        lifespan=lifespan,
    )
    app.state.container = container
    app.include_router(build_health_router())
    app.include_router(build_workflow_router(container.workflow_service))
    app.include_router(build_execution_router(container.execution_service))
    register_exception_handlers(app)
    return app


def serve() -> None:
    """Run the API. Host and port come from WORKFLOW_HOST and WORKFLOW_PORT."""
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        "workflow_engine.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
