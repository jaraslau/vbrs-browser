import { describe, expect, it } from "vitest";

import { buildPageWindow, totalPages } from "./pagination";

describe("buildPageWindow", () => {
  it("returns an empty window when there is a single page", () => {
    expect(buildPageWindow(1, 1)).toEqual([]);
  });

  it("shows all pages when there are few", () => {
    expect(buildPageWindow(2, 4)).toEqual([1, 2, 3, 4]);
  });

  it("shows a window around the current page with gap markers", () => {
    expect(buildPageWindow(5, 10)).toEqual([
      1,
      "ellipsis",
      3,
      4,
      5,
      6,
      7,
      "ellipsis",
      10,
    ]);
  });

  it("handles the first page", () => {
    expect(buildPageWindow(1, 8)).toEqual([1, 2, 3, "ellipsis", 8]);
  });

  it("handles the last page", () => {
    expect(buildPageWindow(8, 8)).toEqual([1, "ellipsis", 6, 7, 8]);
  });
});

describe("totalPages", () => {
  it("ceils the division", () => {
    expect(totalPages(10, 25)).toBe(3);
  });

  it("reports whole pages for an exact multiple", () => {
    expect(totalPages(10, 20)).toBe(2);
  });

  it("reports a single page when everything fits on it", () => {
    expect(totalPages(10, 10)).toBe(1);
  });

  it("never reports fewer than one page", () => {
    expect(totalPages(10, 0)).toBe(1);
  });
});