/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Base URL of the backend API used by the application code.
   * Leave unset/blank to use the same origin (the ``/api`` proxy).
   */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}