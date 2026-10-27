import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { searchArticles } from "../api/articles";
import { searchResultsCache } from "../api/searchResultsCache";
import type { ArticleListResponse } from "../api/types";
import { useArticleSearch } from "./useArticles";

vi.mock("../api/articles", () => ({
  searchArticles: vi.fn(),
  getArticle: vi.fn(),
}));

const search = vi.mocked(searchArticles);

function listing(page = 1, total = 100, pageSize = 10): ArticleListResponse {
  return { items: [], page, page_size: pageSize, total };
}

beforeEach(() => {
  vi.resetAllMocks();
  searchResultsCache.clear();
  search.mockImplementation(async (params) =>
    listing(params?.page, 100, params?.pageSize),
  );
});

describe("search results caching", () => {
  it("pins page one and evicts the least recently accessed other page", async () => {
    const { result, rerender } = renderHook(
      ({ page }) => useArticleSearch("word", page, { cacheResults: true }),
      { initialProps: { page: 1 } },
    );
    const visit = async (page: number): Promise<void> => {
      rerender({ page });
      await waitFor(() => {
        expect(result.current).toMatchObject({
          status: "success",
          data: { page },
        });
      });
    };

    await visit(1);
    await visit(2);
    await visit(3);
    await visit(2);
    await visit(4);
    await visit(1);
    await visit(2);
    expect(search.mock.calls.map(([params]) => params?.page)).toEqual([
      1, 2, 3, 4,
    ]);

    await visit(3);
    expect(search.mock.calls.map(([params]) => params?.page)).toEqual([
      1, 2, 3, 4, 3,
    ]);
  });

  it("reuses cached results after the results page is remounted", async () => {
    const first = renderHook(() =>
      useArticleSearch("word", 1, { cacheResults: true }),
    );
    await waitFor(() => expect(first.result.current.status).toBe("success"));
    first.unmount();

    const second = renderHook(() =>
      useArticleSearch("word", 1, { cacheResults: true }),
    );
    expect(second.result.current).toMatchObject({
      status: "success",
      data: listing(),
    });
    expect(search).toHaveBeenCalledTimes(1);
  });

  it("discards old results when the query or page size changes", async () => {
    const { result, rerender } = renderHook(
      ({ query, pageSize }) =>
        useArticleSearch(query, 1, { pageSize, cacheResults: true }),
      { initialProps: { query: "first", pageSize: 10 } },
    );
    await waitFor(() => expect(result.current.status).toBe("success"));

    for (const props of [
      { query: "second", pageSize: 10 },
      { query: "first", pageSize: 10 },
      { query: "first", pageSize: 20 },
      { query: "first", pageSize: 10 },
    ]) {
      rerender(props);
      expect(result.current.status).toBe("loading");
      await waitFor(() => expect(result.current.status).toBe("success"));
    }
    expect(search).toHaveBeenCalledTimes(5);
  });

  it("does not let live suggestions read or evict the results cache", async () => {
    const full = renderHook(() =>
      useArticleSearch("word", 1, { cacheResults: true }),
    );
    await waitFor(() => expect(full.result.current.status).toBe("success"));
    full.unmount();

    const preview = renderHook(
      ({ query }) => useArticleSearch(query, 1, { pageSize: 6 }),
      { initialProps: { query: "word" } },
    );
    await waitFor(() => expect(preview.result.current.status).toBe("success"));
    expect(preview.result.current).toMatchObject({ data: { page_size: 6 } });
    preview.rerender({ query: "other" });
    await waitFor(() => expect(preview.result.current.status).toBe("success"));
    preview.unmount();

    const restored = renderHook(() =>
      useArticleSearch("word", 1, { cacheResults: true }),
    );
    expect(restored.result.current).toMatchObject({
      status: "success",
      data: { page_size: 10 },
    });
    expect(search).toHaveBeenCalledTimes(3);
  });

  it("ignores aborted responses without putting them in the cache", async () => {
    let resolveOld: (data: ArticleListResponse) => void = () => {};
    search.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        }),
    );
    const { result, rerender } = renderHook(
      ({ page }) => useArticleSearch("word", page, { cacheResults: true }),
      { initialProps: { page: 2 } },
    );
    const signal = search.mock.calls[0][1];
    rerender({ page: 3 });
    expect(signal?.aborted).toBe(true);
    await waitFor(() => expect(result.current.status).toBe("success"));
    await act(async () => resolveOld(listing(2, 999)));
    expect(result.current).toMatchObject({ data: { page: 3, total: 100 } });

    rerender({ page: 2 });
    expect(result.current.status).toBe("loading");
    await waitFor(() => {
      expect(result.current).toMatchObject({ data: { page: 2, total: 100 } });
    });
    expect(search).toHaveBeenCalledTimes(3);
  });

  it("does not cache failures and lets retry refresh successful results", async () => {
    search.mockRejectedValueOnce(new Error("Unavailable"));
    const { result, rerender } = renderHook(
      ({ page }) => useArticleSearch("word", page, { cacheResults: true }),
      { initialProps: { page: 1 } },
    );
    await waitFor(() => expect(result.current.status).toBe("error"));
    rerender({ page: 2 });
    await waitFor(() => expect(result.current.status).toBe("success"));
    rerender({ page: 1 });
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(search).toHaveBeenCalledTimes(3);

    search.mockResolvedValueOnce(listing(1, 200));
    act(() => result.current.retry());
    await waitFor(() => {
      expect(result.current).toMatchObject({ data: { total: 200 } });
    });
    expect(search).toHaveBeenCalledTimes(4);
  });
});
