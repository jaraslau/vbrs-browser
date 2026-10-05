import { describe, expect, it } from "vitest";

import { parsePositiveInt } from "./query";

describe("parsePositiveInt", () => {
  it("falls back when the value is missing", () => {
    expect(parsePositiveInt(null, 1)).toBe(1);
  });

  it("parses valid positive integers", () => {
    expect(parsePositiveInt("3", 1)).toBe(3);
  });

  it("falls back for non-numeric values", () => {
    expect(parsePositiveInt("abc", 1)).toBe(1);
  });

  it("falls back for non-positive values", () => {
    expect(parsePositiveInt("0", 1)).toBe(1);
    expect(parsePositiveInt("-1", 1)).toBe(1);
  });
});