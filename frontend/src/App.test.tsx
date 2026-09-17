import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { searchArticles } from "./api/articles";
import type { ArticleListResponse } from "./api/types";

import App from "./App";

vi.mock("./api/articles", () => ({
  searchArticles: vi.fn(),
  getArticle: vi.fn(),
}));

const mockedSearchArticles = vi.mocked(searchArticles);

function emptyListing(): ArticleListResponse {
  return { items: [], page: 1, page_size: 20, total: 0 };
}

describe("App", () => {
  it("renders the application title and the search page", async () => {
    mockedSearchArticles.mockResolvedValue(emptyListing());

    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "vbrs-browser" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("No articles in the dictionary yet."),
    ).toBeInTheDocument();
  });
});