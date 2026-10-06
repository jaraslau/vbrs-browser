import type { CSSProperties } from "react";
import { Link, useLocation } from "react-router-dom";

import { LIVE_SEARCH_OPTIONS } from "../api/config";
import { useArticleSearch } from "../hooks/useArticles";

export function LiveSearchResults({ query }: { query: string }) {
  const location = useLocation();
  const search = useArticleSearch(query, 1, LIVE_SEARCH_OPTIONS);

  return (
    <section
      className="live-search"
      aria-label="Live matches"
      aria-busy={search.status === "loading"}
    >
      <p className="live-search-status" role="status">
        {search.status === "loading" && "Searching…"}
        {search.status === "success" &&
          (search.data.items.length === 0
            ? "No matching words."
            : `${search.data.total} ${search.data.total === 1 ? "match" : "matches"}`)}
        {search.status === "error" && "Live search unavailable."}
      </p>
      {search.status === "error" && (
        <button
          className="live-search-retry"
          type="button"
          onClick={search.retry}
        >
          Try again
        </button>
      )}
      {search.status === "success" && (
        <ol className="live-search-list" aria-label="Suggested words">
          {search.data.items
            .slice(0, LIVE_SEARCH_OPTIONS.pageSize)
            .map((article, index) => (
              <li
                key={article.id}
                style={{ "--suggestion-index": index } as CSSProperties}
              >
                <Link
                  to={`/articles/${encodeURIComponent(article.id)}`}
                  state={{ backgroundLocation: location }}
                >
                  <span className="live-search-number" aria-hidden="true">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="live-search-word">{article.word}</span>
                  <span className="live-search-arrow" aria-hidden="true">
                    ↗
                  </span>
                </Link>
              </li>
            ))}
        </ol>
      )}
    </section>
  );
}
