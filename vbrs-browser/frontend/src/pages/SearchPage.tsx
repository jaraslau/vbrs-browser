/**
 * Search page: the application's home route.
 *
 * The search query and page number live in the URL query string
 * (``?q=...&page=...``) so results are bookmarkable and browser navigation
 * works naturally. The form is submit-based — no request fires per keystroke.
 */

import { useSearchParams } from "react-router-dom";

import { parsePositiveInt } from "../lib/query";
import { EmptyMessage, ErrorMessage, LoadingMessage } from "../components/StatusMessage";
import { Pagination } from "../components/Pagination";
import { ResultsList } from "../components/ResultsList";
import { SearchForm } from "../components/SearchForm";
import { useArticleSearch } from "../hooks/useArticles";

/** "1 article" for one, "N articles" otherwise. */
function pluralizedArticleCount(total: number): string {
  return total === 1 ? "1 article" : `${total} articles`;
}

/** Summary line describing the current result set. */
function resultsSummary(total: number, query: string): string {
  if (query === "") {
    return pluralizedArticleCount(total);
  }
  return `${pluralizedArticleCount(total)} found for "${query}"`;
}

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") ?? "";
  const page = parsePositiveInt(searchParams.get("page"), 1);
  const search = useArticleSearch(query, page);

  /** Update the URL with a new query, resetting pagination to page 1. */
  const handleSearch = (nextQuery: string) => {
    const nextParams = new URLSearchParams();
    if (nextQuery !== "") {
      nextParams.set("q", nextQuery);
    }
    setSearchParams(nextParams);
  };

  /** Update the URL with a new page, keeping the current query. */
  const handlePageChange = (nextPage: number) => {
    const nextParams = new URLSearchParams();
    if (query !== "") {
      nextParams.set("q", query);
    }
    if (nextPage > 1) {
      nextParams.set("page", String(nextPage));
    }
    setSearchParams(nextParams);
  };

  return (
    <section className="search-page">
      <h2>Search the dictionary</h2>
      <SearchForm defaultQuery={query} onSearch={handleSearch} />

      {search.status === "loading" && <LoadingMessage />}

      {search.status === "error" && (
        <ErrorMessage message={search.message} onRetry={search.retry} />
      )}

      {search.status === "success" && (
        <>
          <p className="results-summary" role="status">
            {resultsSummary(search.data.total, query)}
          </p>

          {search.data.items.length === 0 ? (
            query === "" ? (
              <EmptyMessage>
                No articles in the dictionary yet.
              </EmptyMessage>
            ) : (
              <EmptyMessage>
                No articles match "{query}". Try a different search.
              </EmptyMessage>
            )
          ) : (
            <ResultsList articles={search.data.items} />
          )}

          <Pagination
            page={search.data.page}
            pageSize={search.data.page_size}
            total={search.data.total}
            onPageChange={handlePageChange}
          />
        </>
      )}
    </section>
  );
}