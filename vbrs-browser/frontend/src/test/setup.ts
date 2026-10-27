/// <reference types="vitest/jsdom" />

import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Use browser storage rather than Node's built-in Web Storage in DOM tests.
vi.stubGlobal("localStorage", jsdom.window.localStorage);

// jsdom has no layout engine; browser checks exercise real resize observations.
vi.stubGlobal(
  "ResizeObserver",
  class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  },
);
