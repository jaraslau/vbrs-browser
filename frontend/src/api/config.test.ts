import { describe, expect, it } from "vitest";

import { getApiConfig, resolveApiBaseUrl } from "./config";

describe("resolveApiBaseUrl", () => {
  it("defaults to /api/v1 when the variable is unset", () => {
    expect(resolveApiBaseUrl({})).toBe("/api/v1");
  });

  it("defaults to /api/v1 when the variable is blank or whitespace", () => {
    expect(resolveApiBaseUrl({ VITE_API_BASE_URL: "" })).toBe("/api/v1");
    expect(resolveApiBaseUrl({ VITE_API_BASE_URL: "   " })).toBe("/api/v1");
  });

  it("uses the configured base URL", () => {
    expect(
      resolveApiBaseUrl({ VITE_API_BASE_URL: "http://localhost:8000/api/v1" }),
    ).toBe("http://localhost:8000/api/v1");
  });

  it("strips trailing slashes from the configured base URL", () => {
    expect(
      resolveApiBaseUrl({ VITE_API_BASE_URL: "http://localhost:8000/api/v1/" }),
    ).toBe("http://localhost:8000/api/v1");
  });

  it("ignores non-string values", () => {
    expect(resolveApiBaseUrl({ VITE_API_BASE_URL: 42 })).toBe("/api/v1");
  });
});

describe("getApiConfig", () => {
  it("resolves the config from the current environment", () => {
    expect(getApiConfig().baseUrl).toBe("/api/v1");
  });
});