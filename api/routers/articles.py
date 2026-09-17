"""Article search and detail routes for the vbrs-browser API.

The router stays thin: query parameters are validated by
:class:`api.models.api.SearchQuery`, business rules live in
:class:`api.services.articles.ArticleService`, and Elasticsearch access stays
inside the repository. None of the Elasticsearch response shapes ever reach
this layer.
"""

from __future__ import annotations

from elasticsearch import Elasticsearch
from fastapi import APIRouter, Depends

from api.config.settings import Settings, get_settings
from api.elasticsearch.client import get_elasticsearch_client
from api.models.api import (
    ArticleListResponse,
    ArticleResponse,
    ErrorResponse,
    SearchQuery,
)
from api.repositories.articles import ArticleRepository
from api.services.articles import ArticleService

router = APIRouter(prefix="/articles", tags=["articles"])


def get_article_repository(
    es_client: Elasticsearch = Depends(get_elasticsearch_client),
    settings: Settings = Depends(get_settings),
) -> ArticleRepository:
    """Build the repository bound to the shared Elasticsearch client."""
    return ArticleRepository(client=es_client, index=settings.es_index)


def get_article_service(
    repository: ArticleRepository = Depends(get_article_repository),
    settings: Settings = Depends(get_settings),
) -> ArticleService:
    """Build the article service with the configured pagination limits."""
    return ArticleService(repository=repository, settings=settings)


@router.get(
    "",
    response_model=ArticleListResponse,
    summary="Search or list dictionary articles",
    description=(
        "Search dictionary articles by free text across the headword, latin "
        "transliteration, and definition text (``q``). When ``q`` is missing "
        "or blank the endpoint returns a deterministic paginated listing of "
        "every article. ``page_size`` defaults to the configured value and is "
        "clamped to the configured maximum; the effective value is echoed "
        "back in the response so clients can paginate."
    ),
    responses={
        422: {
            "description": "Invalid query parameters (page, page_size)",
            "model": ErrorResponse,
        }
    },
)
def list_articles(
    params: SearchQuery = Depends(),
    service: ArticleService = Depends(get_article_service),
) -> ArticleListResponse:
    """Return one page of matching articles."""
    return service.search(params)


@router.get(
    "/{article_id}",
    response_model=ArticleResponse,
    summary="Get a dictionary article by ID",
    description=(
        "Return the complete dictionary article addressed by its stable "
        "Elasticsearch document ID. A 404 response is returned when no "
        "article with the given ID exists."
    ),
    responses={404: {"description": "Article not found", "model": ErrorResponse}},
)
def get_article(
    article_id: str,
    service: ArticleService = Depends(get_article_service),
) -> ArticleResponse:
    """Return one full dictionary article."""
    return service.get_article(article_id)
