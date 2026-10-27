/**
 * Data-fetching hooks for the article API.
 *
 * Each hook owns the loading/success/error lifecycle for one request shape
 * and exposes a stable ``retry`` callback so the UI can re-run a failed
 * request. Requests are abortable and out-of-order responses are discarded.
 */

import { useContext, useEffect, useState } from "react";

import { searchArticles, getArticle } from "../api/articles";
import { ApiError, toErrorMessage } from "../api/client";
import { searchResultsCache } from "../api/searchResultsCache";
import type { Article, ArticleListResponse } from "../api/types";
import { SearchOptionsContext } from "../contexts/SearchOptionsContext";
import { normalizeSearchQuery } from "../lib/searchOptions";

/** Discriminated state of an article search request. */
export type SearchState =
  | { status: "loading" }
  | { status: "success"; data: ArticleListResponse }
  | { status: "error"; message: string };

/** Discriminated state of a single-article request. */
export type ArticleState =
  | { status: "loading" }
  | { status: "success"; article: Article }
  | { status: "error"; message: string; notFound: boolean };

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

/**
 * Search articles for the given query and page.
 *
 * Re-runs whenever ``query``, ``page`` or the internal retry counter
 * changes. The returned object also exposes a ``retry`` function that
 * re-triggers the request without changing the URL parameters.
 */
export function useArticleSearch(
  query: string,
  page: number,
  {
    pageSize,
    debounceMs = 0,
    cacheResults = false,
  }: { pageSize?: number; debounceMs?: number; cacheResults?: boolean } = {},
): SearchState & { retry: () => void } {
  const searchOptions = useContext(SearchOptionsContext);
  const effectiveQuery = normalizeSearchQuery(query, searchOptions);
  const scope = JSON.stringify([effectiveQuery.trim(), pageSize ?? null]);
  const requestKey = JSON.stringify([scope, page]);
  const [retryKey, setRetryKey] = useState(0);
  const [state, setState] = useState<SearchState & { requestKey: string }>({
    status: "loading",
    requestKey,
  });

  useEffect(() => {
    if (cacheResults) {
      const cached = searchResultsCache.get(scope, page);
      if (cached !== undefined) {
        setState({ status: "success", data: cached, requestKey });
        return;
      }
    }

    const controller = new AbortController();
    let stale = false;

    setState({ status: "loading", requestKey });
    const load = () =>
      searchArticles(
        {
          q: effectiveQuery,
          page,
          ...(pageSize === undefined ? {} : { pageSize }),
        },
        controller.signal,
      )
        .then((data) => {
          if (!stale) {
            if (cacheResults) searchResultsCache.set(scope, page, data);
            setState({ status: "success", data, requestKey });
          }
        })
        .catch((error: unknown) => {
          if (stale || isAbortError(error)) {
            return;
          }
          setState({
            status: "error",
            message: toErrorMessage(error),
            requestKey,
          });
        });

    const timer = debounceMs > 0 ? setTimeout(load, debounceMs) : undefined;
    if (debounceMs === 0) {
      void load();
    }

    return () => {
      stale = true;
      clearTimeout(timer);
      controller.abort();
    };
  }, [
    effectiveQuery,
    page,
    pageSize,
    debounceMs,
    retryKey,
    cacheResults,
    scope,
    requestKey,
  ]);

  return {
    ...(state.requestKey === requestKey
      ? state
      : { status: "loading" as const }),
    retry: () => {
      if (cacheResults) searchResultsCache.delete(scope, page);
      setRetryKey((key) => key + 1);
    },
  };
}

/**
 * Fetch the article with the given ID.
 *
 * Re-runs whenever ``articleId`` or the internal retry counter changes.
 * When the article does not exist the error state carries ``notFound: true``
 * and a message taken from the API's 404 ``detail`` field.
 */
export function useArticle(
  articleId: string,
): ArticleState & { retry: () => void } {
  const [retryKey, setRetryKey] = useState(0);
  const [state, setState] = useState<ArticleState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    let stale = false;

    setState({ status: "loading" });
    getArticle(articleId, controller.signal)
      .then((article) => {
        if (!stale) {
          setState({ status: "success", article });
        }
      })
      .catch((error: unknown) => {
        if (stale || isAbortError(error)) {
          return;
        }
        setState({
          status: "error",
          message: toErrorMessage(error),
          notFound: error instanceof ApiError && error.status === 404,
        });
      });

    return () => {
      stale = true;
      controller.abort();
    };
  }, [articleId, retryKey]);

  return {
    ...state,
    retry: () => setRetryKey((key) => key + 1),
  };
}
