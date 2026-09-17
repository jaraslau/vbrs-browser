"""Application service for article search and retrieval.

The service layer translates validated API request models into repository
calls and maps repository results back into API response models. It owns the
only business rules here:

* defaulting and clamping ``page_size`` against the configured limits, and
* deciding that a missing article is a :class:`ArticleNotFoundError`.

The service knows nothing about HTTP: FastAPI-specific concerns (status
codes, request/response serialization) live in the routers.
"""

from __future__ import annotations

from api.config.settings import Settings
from api.models.api import ArticleListResponse, ArticleResponse, SearchQuery
from api.repositories.articles import ArticleRepository


class ArticleNotFoundError(LookupError):
    """Raised when the requested article does not exist in the index.

    Attributes:
        article_id: The stable document ID that could not be resolved.
    """

    def __init__(self, article_id: str) -> None:
        super().__init__(f"Article {article_id!r} not found")
        self.article_id = article_id


class ArticleService:
    """Search and retrieve dictionary articles through the repository."""

    def __init__(self, repository: ArticleRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    def search(self, params: SearchQuery) -> ArticleListResponse:
        """Run a search or deterministic listing for validated request params.

        ``params.page_size`` is resolved before talking to the repository:
        when omitted the configured default page size applies, and any value
        above the configured maximum is clamped down to it. The effective
        page size is echoed back in the response so clients can paginate.
        """
        page_size = self._resolve_page_size(params.page_size)
        page = self._repository.search_articles(
            query=params.q,
            page=params.page,
            page_size=page_size,
        )
        return ArticleListResponse(
            items=[ArticleResponse.from_article(stored.id, stored.data) for stored in page.items],
            page=params.page,
            page_size=page_size,
            total=page.total,
        )

    def get_article(self, article_id: str) -> ArticleResponse:
        """Return the full article for ``article_id``.

        Raises:
            ArticleNotFoundError: When no article with ``article_id`` exists.
        """
        stored = self._repository.get_article(article_id)
        if stored is None:
            raise ArticleNotFoundError(article_id)
        return ArticleResponse.from_article(stored.id, stored.data)

    def _resolve_page_size(self, requested: int | None) -> int:
        """Resolve a request page size to the effective value.

        ``None`` falls back to the configured default; anything above the
        configured maximum is clamped so callers cannot force unbounded pages.
        """
        if requested is None:
            return self._settings.page_size
        return min(requested, self._settings.max_page_size)
