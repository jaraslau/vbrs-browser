/**
 * API base-URL resolution.
 *
 * The base URL is configuration-driven through the ``VITE_API_BASE_URL``
 * environment variable. When it is unset or blank the client talks to the
 * same origin that serves the application and relies on the ``/api`` proxy
 * (Vite dev server or nginx in production), exactly as documented in the
 * repository README.
 */

/** Environment-shaped object exposing frontend build-time variables. */
export type FrontendEnv = Record<string, string | number | boolean | undefined>;

/** Fully resolved API configuration used by the HTTP client. */
export interface ApiConfig {
  /**
   * Base URL prefix for every API request, including the versioned
   * ``/api/v1`` path segment, without a trailing slash.
   */
  baseUrl: string;
}

const DEFAULT_API_BASE_URL = "/api/v1";

function stripTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, "");
}

/**
 * Resolve the API base URL from an environment object.
 *
 * @param env Environment variables; defaults to Vite's ``import.meta.env``.
 */
export function resolveApiBaseUrl(env: FrontendEnv = import.meta.env): string {
  const configured = env.VITE_API_BASE_URL;
  if (typeof configured === "string" && configured.trim() !== "") {
    return stripTrailingSlashes(configured);
  }
  return DEFAULT_API_BASE_URL;
}

/** Build the API configuration from the current environment. */
export function getApiConfig(): ApiConfig {
  return { baseUrl: resolveApiBaseUrl() };
}