"""Consistent JSON error handling for the vbrs-browser API.

Every failure that escapes the route handlers is reduced to the same JSON
shape FastAPI already uses for validation errors -- ``{"detail": ...}`` -- so
the frontend can rely on one error contract.

Backend failures (Elasticsearch problems, malformed repository responses,
unhandled exceptions) are logged with context before being converted into a
client-safe message: internal details and raw Elasticsearch responses are
never leaked to the frontend.
"""

from __future__ import annotations

import logging
from typing import cast

from elasticsearch import (
    ApiError as EsApiError,
    ConnectionError as EsConnectionError,
    ConnectionTimeout as EsConnectionTimeout,
    NotFoundError as EsNotFoundError,
    TransportError as EsTransportError,
)
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.repositories.articles import RepositoryResponseError
from backend.services.articles import ArticleNotFoundError

logger = logging.getLogger(__name__)

_SERVICE_UNAVAILABLE = "The search backend is temporarily unavailable."
_SERVICE_ERROR = "The search backend returned an error."
_UNEXPECTED_RESPONSE = "The search backend returned an unexpected response."
_INTERNAL_ERROR = "An internal error occurred."


def _error_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast(StarletteHTTPException, exc)
    return _error_response(http_exc.status_code, str(http_exc.detail))


async def _article_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, str(exc))


async def _es_connection_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Elasticsearch connection failed: %r", exc)
    return _error_response(status.HTTP_503_SERVICE_UNAVAILABLE, _SERVICE_UNAVAILABLE)


async def _es_timeout_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Elasticsearch request timed out: %r", exc)
    return _error_response(status.HTTP_503_SERVICE_UNAVAILABLE, _SERVICE_UNAVAILABLE)


async def _es_transport_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Elasticsearch transport error: %r", exc)
    return _error_response(status.HTTP_502_BAD_GATEWAY, _SERVICE_ERROR)


async def _es_api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Elasticsearch request failed: %r", exc)
    return _error_response(status.HTTP_502_BAD_GATEWAY, _SERVICE_ERROR)


async def _es_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Elasticsearch resource not found: %r", exc)
    return _error_response(status.HTTP_503_SERVICE_UNAVAILABLE, _SERVICE_UNAVAILABLE)


async def _repository_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Malformed Elasticsearch response: %r", exc)
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, _UNEXPECTED_RESPONSE)


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while serving %s", request.url.path)
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, _INTERNAL_ERROR)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the error handlers above to ``app``.

    Handlers are looked up by walking the raised exception's MRO, so the
    most specific registered type wins (e.g. ``ConnectionError`` is handled
    before the general ``EsTransportError``).
    """
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(ArticleNotFoundError, _article_not_found_handler)
    app.add_exception_handler(EsConnectionError, _es_connection_error_handler)
    app.add_exception_handler(EsConnectionTimeout, _es_timeout_handler)
    app.add_exception_handler(EsNotFoundError, _es_not_found_handler)
    app.add_exception_handler(EsTransportError, _es_transport_error_handler)
    app.add_exception_handler(EsApiError, _es_api_error_handler)
    app.add_exception_handler(RepositoryResponseError, _repository_error_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
