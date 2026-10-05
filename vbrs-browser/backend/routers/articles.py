from __future__ import annotations

from typing import Annotated

from elasticsearch import Elasticsearch
from fastapi import APIRouter, Depends

from backend.config.settings import Settings, get_settings
from backend.elasticsearch.client import get_elasticsearch_client
from backend.models.api import (
    ArticleListResponse,
    ArticleResponse,
    ErrorResponse,
    SearchQuery,
)
from backend.repositories.articles import ArticleRepository
from backend.services.articles import ArticleService

router = APIRouter(prefix="/articles", tags=["articles"])


def get_article_repository(
    es_client: Annotated[Elasticsearch, Depends(get_elasticsearch_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ArticleRepository:
    return ArticleRepository(client=es_client, index=settings.es_index)


def get_article_service(
    repository: Annotated[ArticleRepository, Depends(get_article_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ArticleService:
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
    params: Annotated[SearchQuery, Depends()],
    service: Annotated[ArticleService, Depends(get_article_service)],
) -> ArticleListResponse:
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
    service: Annotated[ArticleService, Depends(get_article_service)],
) -> ArticleResponse:
    return service.get_article(article_id)
