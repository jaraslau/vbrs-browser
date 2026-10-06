import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PageScrollbar } from "./PageScrollbar";

describe("PageScrollbar", () => {
  let resize: () => void;
  const disconnect = vi.fn();

  beforeEach(() => {
    disconnect.mockClear();
    vi.spyOn(document.documentElement, "scrollHeight", "get").mockReturnValue(
      4000,
    );
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(800);
    vi.stubGlobal("innerHeight", 1000);
    vi.stubGlobal("scrollY", 0);
    vi.stubGlobal("scrollTo", vi.fn());
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(callback: () => void) {
          resize = callback;
        }
        observe(): void {}
        disconnect = disconnect;
      },
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("tracks page position and sizes the thumb proportionally", () => {
    render(<PageScrollbar />);
    const slider = screen.getByRole("slider");
    expect(slider).toHaveValue("0");
    expect(slider.style.getPropertyValue("--thumb-size")).toBe("200px");

    vi.stubGlobal("scrollY", 1500);
    fireEvent.scroll(window);
    expect(slider).toHaveValue("500");
    expect(slider).toHaveAttribute("aria-valuetext", "50% of page");

    vi.stubGlobal("innerHeight", 2000);
    act(() => resize());
    expect(slider.style.getPropertyValue("--thumb-size")).toBe("400px");
    expect(slider).toHaveValue("750");
  });

  it("scrolls directly to the selected track position", () => {
    render(<PageScrollbar />);
    fireEvent.change(screen.getByRole("slider"), { target: { value: "750" } });
    expect(window.scrollTo).toHaveBeenCalledWith({
      top: 2250,
      behavior: "instant",
    });
  });

  it.each([
    ["Home", 0],
    ["End", 3000],
    ["ArrowUp", 1460],
    ["ArrowDown", 1540],
    ["PageUp", 500],
    ["PageDown", 2500],
  ])("supports %s navigation", (key, top) => {
    vi.stubGlobal("scrollY", 1500);
    render(<PageScrollbar />);
    fireEvent.keyDown(screen.getByRole("slider"), { key });
    expect(window.scrollTo).toHaveBeenCalledWith({ top, behavior: "instant" });
  });

  it("clamps keyboard movement to the page boundaries", () => {
    render(<PageScrollbar />);
    fireEvent.keyDown(screen.getByRole("slider"), { key: "ArrowUp" });
    expect(window.scrollTo).toHaveBeenLastCalledWith({
      top: 0,
      behavior: "instant",
    });
    vi.stubGlobal("scrollY", 2900);
    fireEvent.keyDown(screen.getByRole("slider"), { key: "PageDown" });
    expect(window.scrollTo).toHaveBeenLastCalledWith({
      top: 3000,
      behavior: "instant",
    });
  });

  it("hides when content fits and reappears when content grows", () => {
    const height = vi
      .spyOn(document.documentElement, "scrollHeight", "get")
      .mockReturnValue(0);
    render(<PageScrollbar />);
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
    expect(
      screen
        .getByRole("slider", { hidden: true })
        .style.getPropertyValue("--thumb-size"),
    ).not.toContain("NaN");
    height.mockReturnValue(4000);
    act(() => resize());
    expect(screen.getByRole("slider")).toBeVisible();
  });

  it("disconnects observation when unmounted", () => {
    const { unmount } = render(<PageScrollbar />);
    unmount();
    expect(disconnect).toHaveBeenCalledOnce();
  });
});
