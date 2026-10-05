import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  buildApiUrl,
  requestJson,
  toErrorMessage,
} from "./client";

describe("buildApiUrl", () => {
  it("joins the base URL and endpoint", () => {
    expect(buildApiUrl("/api/v1", "/articles")).toBe("/api/v1/articles");
  });

  it("tolerates trailing slashes on either part", () => {
    expect(buildApiUrl("http://localhost:8000/api/v1/", "articles/")).toBe(
      "http://localhost:8000/api/v1/articles",
    );
  });

  it("appends non-empty query parameters", () => {
    const query = new URLSearchParams({ q: "гад" });
    expect(buildApiUrl("/api/v1", "articles", query)).toBe(
      "/api/v1/articles?q=%D0%B3%D0%B0%D0%B4",
    );
  });

  it("omits empty or missing query parameters", () => {
    expect(buildApiUrl("/api/v1", "articles", new URLSearchParams())).toBe(
      "/api/v1/articles",
    );
    expect(buildApiUrl("/api/v1", "articles")).toBe("/api/v1/articles");
  });
});

function stubFetch(response: Partial<Response>): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({}),
    ...response,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("requestJson", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed JSON body for a successful response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ items: [], page: 1, page_size: 20, total: 0 }),
      }),
    );

    await expect(requestJson("/articles")).resolves.toEqual({
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
    });
  });

  it("requests the configured base URL with query parameters", async () => {
    const fetchMock = stubFetch({});
    const query = new URLSearchParams({ q: "gadalin", page: "1" });

    await requestJson("/articles", { query });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/articles?q=gadalin&page=1",
      expect.objectContaining({
        method: "GET",
        headers: { Accept: "application/json" },
      }),
    );
  });

  it("forwards an abort signal to fetch", async () => {
    const fetchMock = stubFetch({});
    const controller = new AbortController();

    await requestJson("/articles", { signal: controller.signal });

    expect(fetchMock.mock.calls[0][1]).toEqual(
      expect.objectContaining({ signal: controller.signal }),
    );
  });

  it("throws an ApiError carrying the status and detail from the body", async () => {
    stubFetch({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Article 'doc-1' not found" }),
    });

    const caught = await requestJson("/articles/doc-1").catch(
      (error: unknown) => error,
    );

    expect(caught).toBeInstanceOf(ApiError);
    if (caught instanceof ApiError) {
      expect(caught.status).toBe(404);
      expect(caught.message).toBe("Article 'doc-1' not found");
    }
  });

  it("falls back to a generic message when the error body is not JSON", async () => {
    stubFetch({
      ok: false,
      status: 503,
      json: async () => {
        throw new SyntaxError("Unexpected token");
      },
    });

    const caught = await requestJson("/articles").catch(
      (error: unknown) => error,
    );

    expect(caught).toBeInstanceOf(ApiError);
    if (caught instanceof ApiError) {
      expect(caught.status).toBe(503);
      expect(caught.message).toContain("The request failed");
    }
  });
});

describe("toErrorMessage", () => {
  it("prefers the message of an ApiError", () => {
    expect(toErrorMessage(new ApiError(503, "Unavailable"))).toBe(
      "Unavailable",
    );
  });

  it("uses the message of ordinary errors", () => {
    expect(toErrorMessage(new Error("boom"))).toBe("boom");
  });

  it("returns a generic message for non-Error values", () => {
    expect(toErrorMessage("nope")).toBe("An unexpected error occurred.");
  });
});