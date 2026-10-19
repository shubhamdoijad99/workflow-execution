"""Liveness route."""

from fastapi import APIRouter


class HealthController:
    def health(self) -> dict[str, str]:
        return {"status": "ok"}

    def root(self) -> dict[str, str]:
        return {
            "service": "workflow-engine",
            "health": "/health",
            "docs": "/docs",
        }


def build_health_router() -> APIRouter:
    controller = HealthController()
    router = APIRouter(tags=["health"])

    @router.get("/health")
    def health() -> dict[str, str]:
        return controller.health()

    @router.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return controller.root()

    return router
