"""Pydantic models describing the HTTP API request/response boundaries.

These models define the JSON contracts exposed by the FastAPI application.
They stay separate from the source-dictionary models because the API surface
adds identifiers and pagination metadata that do not exist in the input data.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from api.models.dictionary import DictionaryArticle


class HealthResponse(BaseModel):
    """Machine-readable service status for ``GET /api/v1/health``.

    Attributes:
        status: Service status; always ``ok`` when the endpoint responds.
        elasticsearch: Elasticsearch connectivity: ``connected`` when the
            configured cluster answered a ping, ``unavailable`` otherwise.
    """

    status: Literal["ok"]
    elasticsearch: Literal["connected", "unavailable"]


class ArticleResponse(DictionaryArticle):
    """A dictionary article as returned by the API, including its stable ID.

    Extends :class:`api.models.dictionary.DictionaryArticle` with the
    Elasticsearch document ID so clients can fetch and link to an article.
    """

    id: str

    @classmethod
    def from_article(cls, article_id: str, article: DictionaryArticle) -> ArticleResponse:
        return cls(id=article_id, **article.model_dump())


class ArticleListResponse(BaseModel):
    """Paginated response for ``GET /api/v1/articles``.

    Attributes:
        items: The articles on the requested page.
        page: 1-based page number of the returned items.
        page_size: Number of items requested per page.
        total: Total number of matching articles across all pages.
    """

    items: list[ArticleResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)


class ErrorResponse(BaseModel):
    """Consistent JSON error payload returned for failed API requests."""

    detail: str


class SearchQuery(BaseModel):
    """Validated query-string parameters for ``GET /api/v1/articles``.

    ``page_size`` is optional: when omitted the API applies the configured
    default page size and clamps the value to the configured maximum.
    """

    q: str | None = Field(
        default=None,
        description=(
            "Free-text search across the headword, latin transliteration, and "
            "definition text. Missing or blank values return a deterministic "
            "paginated listing of every article."
        ),
    )
    page: int = Field(default=1, ge=1, description="1-based page number.")
    page_size: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Number of articles per page. Defaults to the configured page "
            "size and is clamped to the configured maximum."
        ),
    )
