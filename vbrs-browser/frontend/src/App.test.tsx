import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { getArticle, searchArticles } from "./api/articles";
import type { Article, ArticleListResponse } from "./api/types";

import App from "./App";

vi.mock("./api/articles", () => ({
  searchArticles: vi.fn(),
  getArticle: vi.fn(),
}));

const mockedSearchArticles = vi.mocked(searchArticles);
const mockedGetArticle = vi.mocked(getArticle);

const article: Article = {
  id: "doc-1",
  line: 10978,
  word: "ґадалІн",
  latin: "gadalin",
  gender: "м",
  raw: "ґадалІн м. /gadalin/ - гадолиний",
  is_plural: false,
  is_proper: false,
  is_link: false,
  link: null,
  be_notes: [],
  ru_notes: [],
  sources: [],
  definitions: [{ number: "1", text: "гадолиний", ru_notes: [] }],
};

// jsdom lacks native dialog methods; browser checks cover focus and inertness.
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

beforeEach(() => vi.clearAllMocks());

function emptyListing(): ArticleListResponse {
  return { items: [], page: 1, page_size: 20, total: 0 };
}

describe("App", () => {
  it("opens a live match without losing the unsubmitted draft", async () => {
    const user = userEvent.setup();
    mockedSearchArticles.mockImplementation(async (params) =>
      params?.pageSize === undefined
        ? emptyListing()
        : { items: [article], total: 1, page: 1, page_size: params.pageSize },
    );
    mockedGetArticle.mockResolvedValue(article);
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    await screen.findByText("No articles in the dictionary yet.");
    await user.type(screen.getByRole("searchbox"), "gad");
    const suggestions = await screen.findByRole("list", {
      name: "Suggested words",
    });
    await user.click(
      within(suggestions).getByRole("link", { name: "ґадалІн" }),
    );
    const dialog = await screen.findByRole("dialog");
    expect(
      await within(dialog).findByRole("heading", { name: "ґадалІн" }),
    ).toBeInTheDocument();
    await user.click(
      within(dialog).getByRole("button", { name: "Close article" }),
    );
    expect(screen.getByRole("searchbox")).toHaveValue("gad");
    expect(
      screen.getByRole("list", { name: "Suggested words" }),
    ).toBeInTheDocument();
    expect(
      mockedSearchArticles.mock.calls.filter(
        ([params]) => params?.pageSize === undefined,
      ),
    ).toHaveLength(1);
  });

  it.each(["button", "escape", "backdrop"])(
    "opens articles over the current results and restores them on %s dismissal",
    async (method) => {
      const user = userEvent.setup();
      mockedSearchArticles.mockResolvedValue({
        items: [article],
        page: 2,
        page_size: 20,
        total: 40,
      });
      mockedGetArticle.mockResolvedValue(article);
      render(
        <MemoryRouter initialEntries={["/?q=gadalin&page=2"]}>
          <App />
        </MemoryRouter>,
      );

      await user.click(await screen.findByRole("link", { name: /ґадалІн/ }));
      const dialog = await screen.findByRole("dialog", {
        name: "Dictionary article",
      });
      expect(
        await within(dialog).findByRole("heading", { name: "ґадалІн" }),
      ).toBeInTheDocument();
      expect(
        within(dialog).queryByRole("link", { name: /Back to search/ }),
      ).not.toBeInTheDocument();
      expect(screen.getByRole("searchbox")).toHaveValue("gadalin");
      expect(mockedSearchArticles).toHaveBeenCalledTimes(1);

      if (method === "button") {
        await user.click(
          within(dialog).getByRole("button", { name: "Close article" }),
        );
      } else if (method === "escape") {
        fireEvent(dialog, new Event("cancel", { cancelable: true }));
      } else {
        fireEvent.pointerDown(dialog);
        fireEvent.click(dialog);
      }

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      expect(screen.getByRole("searchbox")).toHaveValue("gadalin");
      expect(screen.getByRole("button", { name: "2" })).toHaveAttribute(
        "aria-current",
        "page",
      );
      expect(mockedSearchArticles).toHaveBeenCalledTimes(1);
    },
  );

  it("keeps direct article URLs as standalone pages", async () => {
    mockedGetArticle.mockResolvedValue(article);
    render(
      <MemoryRouter initialEntries={["/articles/doc-1"]}>
        <App />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", { name: "ґадалІн" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Back to search/ }),
    ).toHaveAttribute("href", "/");
  });

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
