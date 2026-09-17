"""FastAPI route handlers for the vbrs-browser backend."""

from api.routers.articles import router as articles_router
from api.routers.health import router as health_router

__all__ = ["articles_router", "health_router"]
