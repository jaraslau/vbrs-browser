import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// jsdom has no layout engine; browser checks exercise real resize observations.
vi.stubGlobal(
  "ResizeObserver",
  class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  },
);
