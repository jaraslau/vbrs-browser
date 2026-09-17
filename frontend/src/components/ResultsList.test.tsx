import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { Article } from "../api/types";

import { ResultsList } from "./ResultsList";

function makeArticle(overrides: Partial<Article> = {}): Article {
  return {
    id: "doc-1",
    line: 10978,
    raw: "ґадалІн м. /gadalin/ - гадолиний",
    word: "ґадалІн",
    latin: "gadalin",
    gender: "м",
    is_plural: false,
    is_proper: false,
    is_link: false,
    be_notes: [],
    ru_notes: [],
    sources: [],
    definitions: [{ number: 1, text: "гадолиний", ru_notes: [] }],
    ...overrides,
  };
}

function renderList(articles: Article[]) {
  return render(
    <MemoryRouter>
      <ResultsList articles={articles} />
    </MemoryRouter>,
  );
}

describe("ResultsList", () => {
  it("shows the word, latin, gender, and first definition and links to the article", () => {
    renderList([makeArticle()]);

    const link = screen.getByRole("link", { name: /ґадалІн/ });
    expect(link).toHaveAttribute("href", "/articles/doc-1");
    expect(within(link).getByText("ґадалІн")).toBeInTheDocument();
    expect(within(link).getByText("gadalin")).toBeInTheDocument();
    expect(within(link).getByText("м")).toBeInTheDocument();
    expect(screen.getByText("гадолиний")).toBeInTheDocument();
  });

  it("renders one entry per article, in order", () => {
    renderList([
      makeArticle({ id: "a", word: "word-a" }),
      makeArticle({ id: "b", word: "word-b" }),
    ]);

    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(within(items[0]).getByText("word-a")).toBeInTheDocument();
    expect(within(items[1]).getByText("word-b")).toBeInTheDocument();
  });

  it("omits latin, gender, and the definition when the article has none", () => {
    renderList([makeArticle({ latin: "", gender: null, definitions: [] })]);

    const link = screen.getByRole("link", { name: /ґадалІн/ });
    expect(link).toBeInTheDocument();
    expect(screen.queryByText("gadalin")).not.toBeInTheDocument();
    expect(screen.queryByText("м")).not.toBeInTheDocument();
    expect(screen.queryByText("гадолиний")).not.toBeInTheDocument();
  });

  it("URL-encodes the article id in the result link", () => {
    renderList([makeArticle({ id: "has space/slash" })]);

    expect(screen.getByRole("link", { name: /ґадалІн/ })).toHaveAttribute(
      "href",
      "/articles/has%20space%2Fslash",
    );
  });

  it("renders nothing when there are no articles", () => {
    const { container } = renderList([]);

    expect(container).toBeEmptyDOMElement();
  });
});
