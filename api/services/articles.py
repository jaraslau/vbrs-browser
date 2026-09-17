from __future__ import annotations

from api.config.settings import Settings
from api.models.api import ArticleListResponse, ArticleResponse, SearchQuery
from api.repositories.articles import ArticleRepository


class ArticleNotFoundError(LookupError):
    def __init__(self, article_id: str) -> None:
        super().__init__(f"Article {article_id!r} not found")
        self.article_id = article_id


class ArticleService:
    def __init__(self, repository: ArticleRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    def search(self, params: SearchQuery) -> ArticleListResponse:
        """Run a search or deterministic listing for validated request params.

        ``params.page_size`` is resolved before talking to the repository:
        when omitted the configured default page size applies, and any value
        above the configured maximum is clamped down to it.
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
        stored = self._repository.get_article(article_id)
        if stored is None:
            raise ArticleNotFoundError(article_id)
        return ArticleResponse.from_article(stored.id, stored.data)

    def _resolve_page_size(self, requested: int | None) -> int:
        if requested is None:
            return self._settings.page_size
        return min(requested, self._settings.max_page_size)
