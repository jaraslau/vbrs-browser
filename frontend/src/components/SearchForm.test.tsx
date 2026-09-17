import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SearchForm } from "./SearchForm";

describe("SearchForm", () => {
  it("renders the supplied query in the input", () => {
    render(<SearchForm defaultQuery="gadalin" onSearch={vi.fn()} />);

    expect(screen.getByLabelText("Search")).toHaveValue("gadalin");
  });

  it("updates the input as the user types without submitting", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(<SearchForm defaultQuery="" onSearch={onSearch} />);

    await user.type(screen.getByLabelText("Search"), "гадал");

    expect(screen.getByLabelText("Search")).toHaveValue("гадал");
    expect(onSearch).not.toHaveBeenCalled();
  });

  it("calls onSearch with the trimmed query when the form is submitted", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(<SearchForm defaultQuery="" onSearch={onSearch} />);

    await user.type(screen.getByLabelText("Search"), "  gadalin  ");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(onSearch).toHaveBeenCalledTimes(1);
    expect(onSearch).toHaveBeenCalledWith("gadalin");
  });

  it("submits when Enter is pressed in the input", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(<SearchForm defaultQuery="" onSearch={onSearch} />);

    await user.type(screen.getByLabelText("Search"), "gadalin{Enter}");

    expect(onSearch).toHaveBeenCalledWith("gadalin");
  });

  it("keeps the input in sync when the query prop changes", () => {
    const { rerender } = render(
      <SearchForm defaultQuery="one" onSearch={vi.fn()} />,
    );
    expect(screen.getByLabelText("Search")).toHaveValue("one");

    rerender(<SearchForm defaultQuery="two" onSearch={vi.fn()} />);
    expect(screen.getByLabelText("Search")).toHaveValue("two");
  });
});
