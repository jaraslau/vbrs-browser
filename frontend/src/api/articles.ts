/**
 * Typed accessors for the article endpoints of the vbrs-browser API.
 *
 * These functions are the only place the application builds article
 * requests; pages and components consume their typed results.
 */

import { requestJson } from "./client";
import type { Article, ArticleListResponse } from "./types";

/** Parameters accepted by {@link searchArticles}. */
export interface SearchArticlesParams {
  /** Free-text query; blank or undefined returns a full listing. */
  q?: string;
  /** 1-based page number. */
  page?: number;
  /** Number of articles per page (the backend applies its own limits). */
  pageSize?: number;
}

/**
 * Search articles by free text, or list all articles when no query is given.
 *
 * Mirrors ``GET /api/v1/articles``.
 */
export async function searchArticles(
  params: SearchArticlesParams = {},
  signal?: AbortSignal,
): Promise<ArticleListResponse> {
  const query = new URLSearchParams();
  if (params.q !== undefined && params.q.trim() !== "") {
    query.set("q", params.q.trim());
  }
  if (params.page !== undefined) {
    query.set("page", String(params.page));
  }
  if (params.pageSize !== undefined) {
    query.set("page_size", String(params.pageSize));
  }
  return requestJson<ArticleListResponse>("/articles", { query, signal });
}

/**
 * Fetch the complete dictionary article with the given stable ID.
 *
 * Mirrors ``GET /api/v1/articles/{article_id}``. Throws {@link ApiError}
 * with status 404 when no such article exists.
 */
export async function getArticle(
  articleId: string,
  signal?: AbortSignal,
): Promise<Article> {
  return requestJson<Article>(`/articles/${encodeURIComponent(articleId)}`, {
    signal,
  });
}