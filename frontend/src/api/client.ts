/**
 * Thin HTTP client for the vbrs-browser API.
 *
 * Keeps all fetch/HTTP concerns in one place: URL construction on top of the
 * configuration-driven base URL, JSON parsing, and normalization of failures
 * into {@link ApiError}. Presentation components never call ``fetch``
 * directly and never see raw ``Response`` objects.
 */

import { getApiConfig } from "./config";
import type { ApiErrorResponse } from "./types";

/** Options accepted by {@link requestJson}. */
export interface RequestOptions {
  /** Query-string parameters appended to the request URL. */
  query?: URLSearchParams;
  /** Abort signal used to cancel an in-flight request. */
  signal?: AbortSignal;
}

/**
 * An API request that failed.
 *
 * Carries the HTTP status code when the backend answered, and a
 * human-readable message taken from the response body's ``detail`` field
 * whenever one is present.
 */
export class ApiError extends Error {
  /** HTTP status code returned by the server. */
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Default message used when a response fails without a JSON body. */
const GENERIC_REQUEST_FAILED = "The request failed.";

/**
 * Join the resolved base URL, an endpoint path, and optional query
 * parameters into a single request URL.
 *
 * @param baseUrl Configuration-driven base URL (no trailing slash).
 * @param endpoint Endpoint path, e.g. ``/articles`` (leading slash optional).
 * @param query Optional query-string parameters.
 */
export function buildApiUrl(
  baseUrl: string,
  endpoint: string,
  query?: URLSearchParams | null,
): string {
  const path = endpoint.replace(/^\/+|\/+$/g, "");
  const base = baseUrl.replace(/\/+$/, "");
  const queryString = query !== undefined && query !== null && query.size > 0
    ? `?${query.toString()}`
    : "";
  return `${base}/${path}${queryString}`;
}

/**
 * Perform a JSON GET request and return the decoded body.
 *
 * @param endpoint Endpoint path relative to the configured API base URL.
 * @param options Query string and abort-signal options.
 * @throws {ApiError} When the server answers with a non-2xx status.
 * @throws {TypeError} When the request cannot be performed (network failure).
 */
export async function requestJson<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const { baseUrl } = getApiConfig();
  const url = buildApiUrl(baseUrl, endpoint, options.query);

  const response = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    signal: options.signal,
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as T;
}

/** Convert a failed response into an {@link ApiError}. */
async function toApiError(response: Response): Promise<ApiError> {
  let detail = `${GENERIC_REQUEST_FAILED} (status ${response.status}).`;
  try {
    const body = (await response.json()) as ApiErrorResponse;
    if (typeof body.detail === "string" && body.detail.trim() !== "") {
      detail = body.detail;
    }
  } catch {
    // The body is not JSON (or is empty); keep the generic message.
  }
  return new ApiError(response.status, detail);
}

/**
 * Turn any thrown value into a human-readable message for the UI.
 *
 * @param error The value caught by the caller.
 */
export function toErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred.";
}