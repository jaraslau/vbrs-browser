import { SEARCH_CACHE_RECENT_PAGE_LIMIT } from "../config";
import type { ArticleListResponse } from "./types";

let activeScope: string | undefined;
const pages = new Map<number, ArticleListResponse>();

// Only the active query/page-size pair is retained, so memory stays bounded.
export const searchResultsCache = {
  get(scope: string, page: number): ArticleListResponse | undefined {
    if (activeScope !== scope) {
      pages.clear();
      activeScope = scope;
    }
    const data = pages.get(page);
    if (data !== undefined) {
      pages.delete(page);
      pages.set(page, data);
    }
    return data;
  },

  set(scope: string, page: number, data: ArticleListResponse): void {
    if (activeScope !== scope) return;
    pages.delete(page);
    pages.set(page, data);

    const recentPages = [...pages.keys()].filter((key) => key !== 1);
    if (recentPages.length > SEARCH_CACHE_RECENT_PAGE_LIMIT) {
      pages.delete(recentPages[0]);
    }
  },

  delete(scope: string, page: number): void {
    if (activeScope === scope) pages.delete(page);
  },

  clear(): void {
    pages.clear();
    activeScope = undefined;
  },
};
