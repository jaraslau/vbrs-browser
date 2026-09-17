"""Data-access layer (Elasticsearch repositories) for the vbrs-browser backend."""

from api.repositories.articles import (
    ArticlePage,
    ArticleRepository,
    BulkIndexResult,
    RepositoryResponseError,
    StoredArticle,
)

__all__ = [
    "ArticlePage",
    "ArticleRepository",
    "BulkIndexResult",
    "RepositoryResponseError",
    "StoredArticle",
]
