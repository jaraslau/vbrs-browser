import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getArticle } from "../api/articles";
import { ApiError } from "../api/client";
import type { Article } from "../api/types";

import { ArticlePage } from "./ArticlePage";

vi.mock("../api/articles", () => ({
  searchArticles: vi.fn(),
  getArticle: vi.fn(),
}));

const mockedGetArticle = vi.mocked(getArticle);

function makeArticle(): Article {
  return {
    id: "doc-1",
    line: 10978,
    raw: "ґадалІніюм, ґадалІн м. /gadalinijum, gadalin/ - гадолиний (Gd)",
    word: "ґадалІніюм, ґадалІн",
    latin: "gadalinijum, gadalin",
    gender: "м",
    is_plural: true,
    is_proper: true,
    is_link: false,
    link: null,
    be_notes: ["Belarusian usage note"],
    ru_notes: ["Gd"],
    sources: ["Слоўнік беларускай мовы"],
    definitions: [
      { number: "1", text: "гадолиний", ru_notes: ["хим. элемент"] },
      { number: "2", text: "другой смысл", ru_notes: [] },
    ],
  };
}

function renderArticlePage(articleId = "doc-1") {
  return render(
    <MemoryRouter initialEntries={[`/articles/${articleId}`]}>
      <Routes>
        <Route path="articles/:articleId" element={<ArticlePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ArticlePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders every dictionary field of the article", async () => {
    mockedGetArticle.mockResolvedValue(makeArticle());

    renderArticlePage();

    expect(
      await screen.findByRole("heading", { name: "ґадалІніюм, ґадалІн" }),
    ).toBeInTheDocument();
    expect(mockedGetArticle).toHaveBeenCalledWith("doc-1", expect.anything());

    // Latin transliteration and gender.
    expect(screen.getByText("gadalinijum, gadalin")).toBeInTheDocument();
    expect(screen.getByText("м")).toBeInTheDocument();

    // Plural and proper-name flags.
    expect(screen.getByText("plural")).toBeInTheDocument();
    expect(screen.getByText("proper name")).toBeInTheDocument();

    // Belarusian and Russian notes.
    expect(screen.getByText("Belarusian usage note")).toBeInTheDocument();
    expect(screen.getByText("Gd")).toBeInTheDocument();

    // Definitions with numbers and per-sense notes.
    expect(screen.getByText("1.")).toBeInTheDocument();
    expect(screen.getByText("гадолиний")).toBeInTheDocument();
    expect(screen.getByText("хим. элемент")).toBeInTheDocument();
    expect(screen.getByText("2.")).toBeInTheDocument();
    expect(screen.getByText("другой смысл")).toBeInTheDocument();

    // Sources and raw text.
    expect(screen.getByText("Слоўнік беларускай мовы")).toBeInTheDocument();
    expect(
      screen.getByText("ґадалІніюм, ґадалІн м. /gadalinijum, gadalin/ - гадолиний (Gd)"),
    ).toBeInTheDocument();

    // Back navigation preserves the search entry point.
    expect(screen.getByRole("link", { name: /Back to search/ })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("shows a loading message while the article request is in flight", () => {
    mockedGetArticle.mockReturnValue(new Promise<Article>(() => {}));

    renderArticlePage();

    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Loading…");
  });

  it("shows a not-found message for a missing article", async () => {
    mockedGetArticle.mockRejectedValue(
      new ApiError(404, "Article 'missing' not found"),
    );

    renderArticlePage("missing");

    expect(
      await screen.findByRole("heading", { name: "Article not found" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Article 'missing' not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to search" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("shows an error message and retries a failed load", async () => {
    const user = userEvent.setup();
    mockedGetArticle
      .mockRejectedValueOnce(new ApiError(503, "The search backend is temporarily unavailable."))
      .mockResolvedValueOnce(makeArticle());

    renderArticlePage();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "The search backend is temporarily unavailable.",
    );

    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(
      await screen.findByRole("heading", { name: "ґадалІніюм, ґадалІн" }),
    ).toBeInTheDocument();
    expect(mockedGetArticle).toHaveBeenCalledTimes(2);
  });
});
