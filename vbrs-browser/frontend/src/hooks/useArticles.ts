/**
 * Data-fetching hooks for the article API.
 *
 * Each hook owns the loading/success/error lifecycle for one request shape
 * and exposes a stable ``retry`` callback so the UI can re-run a failed
 * request. Requests are abortable and out-of-order responses are discarded.
 */

import { useEffect, useState } from "react";

import { searchArticles, getArticle } from "../api/articles";
import { ApiError, toErrorMessage } from "../api/client";
import type { Article, ArticleListResponse } from "../api/types";

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
): SearchState & { retry: () => void } {
  const [retryKey, setRetryKey] = useState(0);
  const [state, setState] = useState<SearchState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    let stale = false;

    setState({ status: "loading" });
    searchArticles({ q: query, page }, controller.signal)
      .then((data) => {
        if (!stale) {
          setState({ status: "success", data });
        }
      })
      .catch((error: unknown) => {
        if (stale || isAbortError(error)) {
          return;
        }
        setState({ status: "error", message: toErrorMessage(error) });
      });

    return () => {
      stale = true;
      controller.abort();
    };
  }, [query, page, retryKey]);

  return {
    ...state,
    retry: () => setRetryKey((key) => key + 1),
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