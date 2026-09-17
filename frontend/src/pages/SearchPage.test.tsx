import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { searchArticles } from "../api/articles";
import { ApiError } from "../api/client";
import type { Article, ArticleListResponse } from "../api/types";

import { SearchPage } from "./SearchPage";

vi.mock("../api/articles", () => ({
  searchArticles: vi.fn(),
  getArticle: vi.fn(),
}));

const mockedSearchArticles = vi.mocked(searchArticles);

function makeArticle(id: string, word: string): Article {
  return {
    id,
    line: 10978,
    raw: `${word} /latin/ - meaning`,
    word,
    latin: "latinus",
    gender: "м",
    is_plural: false,
    is_proper: false,
    is_link: false,
    be_notes: [],
    ru_notes: [],
    sources: [],
    definitions: [{ number: null, text: "meaning", ru_notes: [] }],
  };
}

function listing(
  items: Article[],
  total: number,
  page = 1,
  pageSize = 10,
): ArticleListResponse {
  return { items, page, page_size: pageSize, total };
}

function renderSearchPage(initialEntry = "/") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/" element={<SearchPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SearchPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  it("renders results driven by the query in the URL", async () => {
    mockedSearchArticles.mockResolvedValue(
      listing([makeArticle("doc-1", "ґадалІн")], 1),
    );

    renderSearchPage("/?q=ґадалІн&page=1");

    expect(await screen.findByRole("link", { name: /ґадалІн/ })).toHaveAttribute(
      "href",
      "/articles/doc-1",
    );
    expect(screen.getByText("latinus")).toBeInTheDocument();
    expect(screen.getByText("м")).toBeInTheDocument();
    expect(screen.getByText("meaning")).toBeInTheDocument();
    expect(mockedSearchArticles).toHaveBeenCalledWith(
      { q: "ґадалІн", page: 1 },
      expect.anything(),
    );
  });

  it("shows a summary and does not search on every keystroke", async () => {
    const user = userEvent.setup();
    mockedSearchArticles.mockResolvedValue(listing([], 0));

    renderSearchPage("/");

    expect(await screen.findByText("No articles in the dictionary yet.")).toBeInTheDocument();
    expect(screen.getByText("0 articles")).toBeInTheDocument();

    const input = screen.getByLabelText("Search");
    const searchButton = screen.getByRole("button", { name: "Search" });

    await user.type(input, "gadalin");
    expect(input).toHaveValue("gadalin");

    // Typing alone must not fire a request; only the submit does.
    expect(mockedSearchArticles).toHaveBeenCalledTimes(1);

    await user.click(searchButton);

    await waitFor(() => {
      expect(mockedSearchArticles).toHaveBeenLastCalledWith(
        { q: "gadalin", page: 1 },
        expect.anything(),
      );
    });
    expect(
      await screen.findByText('No articles match "gadalin". Try a different search.'),
    ).toBeInTheDocument();
    expect(screen.getByText('0 articles found for "gadalin"')).toBeInTheDocument();
  });

  it("keeps the query when paginating and resets to page 1 on a new search", async () => {
    const user = userEvent.setup();
    const items = Array.from({ length: 25 }, (_, index) =>
      makeArticle(`doc-${index}`, `word-${index}`),
    );
    mockedSearchArticles.mockImplementation(async (params) =>
      listing(items, 25, params?.page ?? 1),
    );

    renderSearchPage("/?q=gadalin&page=1");

    expect(await screen.findByRole("button", { name: "2" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "2" })).toHaveAttribute(
        "aria-current",
        "page",
      );
    });
    expect(mockedSearchArticles).toHaveBeenLastCalledWith(
      { q: "gadalin", page: 2 },
      expect.anything(),
    );

    await user.click(screen.getByRole("button", { name: "3" }));
    await waitFor(() => {
      expect(mockedSearchArticles).toHaveBeenLastCalledWith(
        { q: "gadalin", page: 3 },
        expect.anything(),
      );
    });

    await user.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => {
      expect(mockedSearchArticles).toHaveBeenLastCalledWith(
        { q: "gadalin", page: 1 },
        expect.anything(),
      );
    });
  });

  it("disables pagination controls at the ends of the result set", async () => {
    mockedSearchArticles.mockResolvedValue(listing(
      [makeArticle("doc-1", "word-1")],
      1,
    ));

    renderSearchPage("/?q=word&page=1");

    await screen.findByRole("link", { name: /word-1/ });

    // A single result fits on one page: no pagination is rendered.
    expect(screen.queryByRole("navigation", { name: "Pagination" })).not.toBeInTheDocument();
  });

  it("shows an error message and retries the failed request", async () => {
    const user = userEvent.setup();
    mockedSearchArticles
      .mockRejectedValueOnce(new ApiError(503, "The search backend is temporarily unavailable."))
      .mockResolvedValueOnce(listing([makeArticle("doc-1", "ґадалІн")], 1));

    renderSearchPage("/?q=ґадалІн");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "The search backend is temporarily unavailable.",
    );

    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByRole("link", { name: /ґадалІн/ })).toBeInTheDocument();
    expect(mockedSearchArticles).toHaveBeenCalledTimes(2);
  });
});