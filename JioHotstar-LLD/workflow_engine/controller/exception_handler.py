"""Map domain errors onto HTTP responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from workflow_engine.exception.errors import WorkflowEngineError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(WorkflowEngineError)
    async def handle_engine_error(
        request: Request,
        exc: WorkflowEngineError,
    ) -> JSONResponse:
        logger.info("%s %s %s", request.method, request.url.path, exc.code)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": str(exc)},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details = []
        for error in exc.errors():
            item = {key: value for key, value in error.items() if key != "ctx"}
            if "input" in item:
                item["input"] = str(item["input"])
            details.append(item)
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Request body is invalid",
                "details": details,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "Internal server error"},
        )
