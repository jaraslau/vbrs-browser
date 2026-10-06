import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { searchArticles } from "../api/articles";
import { LIVE_SEARCH_OPTIONS } from "../api/config";
import type { ArticleListResponse } from "../api/types";
import { LiveSearchResults } from "./LiveSearchResults";

vi.mock("../api/articles", () => ({
  searchArticles: vi.fn(),
  getArticle: vi.fn(),
}));
const search = vi.mocked(searchArticles);

function listing(word: string): ArticleListResponse {
  return {
    total: 1,
    page: 1,
    page_size: LIVE_SEARCH_OPTIONS.pageSize,
    items: [
      {
        id: word,
        word,
        latin: "",
        line: 1,
        raw: word,
        gender: null,
        is_plural: false,
        is_proper: false,
        is_link: false,
        link: null,
        be_notes: [],
        ru_notes: [],
        sources: [],
        definitions: [],
      },
    ],
  };
}

async function finishDebounce(): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(LIVE_SEARCH_OPTIONS.debounceMs);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.resetAllMocks();
});
afterEach(() => vi.useRealTimers());

describe("LiveSearchResults", () => {
  it("debounces typing into one limited request for the latest query", async () => {
    search.mockResolvedValue(listing("гадалін"));
    const { rerender } = render(<LiveSearchResults query="г" />, {
      wrapper: MemoryRouter,
    });
    rerender(<LiveSearchResults query="га" />);
    rerender(<LiveSearchResults query="гад" />);
    expect(search).not.toHaveBeenCalled();
    await finishDebounce();
    expect(search).toHaveBeenCalledTimes(1);
    expect(search).toHaveBeenCalledWith(
      { q: "гад", page: 1, pageSize: LIVE_SEARCH_OPTIONS.pageSize },
      expect.any(AbortSignal),
    );
    expect(screen.getByRole("link", { name: "гадалін" })).toHaveAttribute(
      "href",
      "/articles/%D0%B3%D0%B0%D0%B4%D0%B0%D0%BB%D1%96%D0%BD",
    );
  });

  it("aborts superseded requests and ignores late responses", async () => {
    let resolveOld: (result: ArticleListResponse) => void = () => {};
    search
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveOld = resolve;
          }),
      )
      .mockResolvedValueOnce(listing("new result"));
    const { rerender } = render(<LiveSearchResults query="old" />, {
      wrapper: MemoryRouter,
    });
    await finishDebounce();
    const signal = search.mock.calls[0][1];
    rerender(<LiveSearchResults query="new" />);
    expect(signal?.aborted).toBe(true);
    await finishDebounce();
    await act(async () => resolveOld(listing("stale result")));
    expect(
      screen.getByRole("link", { name: "new result" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("stale result")).not.toBeInTheDocument();
  });

  it("cancels a pending preview when cleared or dismissed", async () => {
    const { unmount } = render(<LiveSearchResults query="gad" />, {
      wrapper: MemoryRouter,
    });
    unmount();
    await finishDebounce();
    expect(search).not.toHaveBeenCalled();
  });

  it("supports retry and empty results", async () => {
    search
      .mockRejectedValueOnce(new Error("Unavailable"))
      .mockResolvedValueOnce({
        items: [],
        total: 0,
        page: 1,
        page_size: LIVE_SEARCH_OPTIONS.pageSize,
      });
    render(<LiveSearchResults query="missing" />, { wrapper: MemoryRouter });
    await finishDebounce();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Live search unavailable.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await finishDebounce();
    expect(screen.getByRole("status")).toHaveTextContent("No matching words.");
  });
});
