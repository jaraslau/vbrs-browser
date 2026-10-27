import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_SEARCH_OPTIONS, SEARCH_OPTIONS_STORAGE_KEY } from "../config";
import {
  normalizeSearchQuery,
  readSearchOptions,
  saveSearchOptions,
} from "./searchOptions";

describe("normalizeSearchQuery", () => {
  it("leaves text unchanged when all rules are off", () => {
    const query = "сi СI и И ау АУ i English";
    expect(normalizeSearchQuery(query, DEFAULT_SEARCH_OPTIONS)).toBe(query);
  });

  it("changes English i only immediately after Cyrillic characters", () => {
    expect(
      normalizeSearchQuery("сi СI бiлi ГI i I ai AI с i с-i 1i", {
        ...DEFAULT_SEARCH_OPTIONS,
        latinI: true,
      }),
    ).toBe("сі СІ білі ГІ i I ai AI с i с-i 1i");
  });

  it("changes Cyrillic и independently and preserves case", () => {
    expect(
      normalizeSearchQuery("и И мир МИР i I сi ау", {
        ...DEFAULT_SEARCH_OPTIONS,
        cyrillicI: true,
      }),
    ).toBe("і І мір МІР i I сi ау");
  });

  it.each(["а", "о", "у", "е", "ю", "ё"])(
    "changes у following %s and preserves case",
    (vowel) => {
      expect(
        normalizeSearchQuery(
          `${vowel}у ${vowel}У ${vowel.toUpperCase()}у ${vowel.toUpperCase()}У`,
          { ...DEFAULT_SEARCH_OPTIONS, shortU: true },
        ),
      ).toBe(
        `${vowel}ў ${vowel}Ў ${vowel.toUpperCase()}ў ${vowel.toUpperCase()}Ў`,
      );
    },
  );

  it("keeps у after other letters, punctuation and spaces", () => {
    const query = "у У бу БУ яу іу ыу эу а у а-у aу";
    expect(
      normalizeSearchQuery(query, { ...DEFAULT_SEARCH_OPTIONS, shortU: true }),
    ).toBe(query);
  });

  it("applies all enabled rules together", () => {
    expect(
      normalizeSearchQuery("сi И ау СI АУ", {
        latinI: true,
        cyrillicI: true,
        shortU: true,
      }),
    ).toBe("сі І аў СІ АЎ");
  });
});

describe("search option storage", () => {
  beforeEach(() => window.localStorage.removeItem(SEARCH_OPTIONS_STORAGE_KEY));
  afterEach(() => vi.restoreAllMocks());

  it("remembers saved preferences", () => {
    const options = { latinI: true, cyrillicI: false, shortU: true };
    saveSearchOptions(options);
    expect(readSearchOptions()).toEqual(options);
  });

  it.each([
    "null",
    "[]",
    "false",
    "invalid JSON",
    '{"latinI":"true","shortU":1}',
  ])("uses safe defaults for invalid stored options: %s", (stored) => {
    window.localStorage.setItem(SEARCH_OPTIONS_STORAGE_KEY, stored);
    expect(readSearchOptions()).toEqual(DEFAULT_SEARCH_OPTIONS);
  });

  it("supports partial saved options", () => {
    window.localStorage.setItem(SEARCH_OPTIONS_STORAGE_KEY, '{"latinI":true}');
    expect(readSearchOptions()).toEqual({
      ...DEFAULT_SEARCH_OPTIONS,
      latinI: true,
    });
  });

  it("works when browser storage is blocked", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("Blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("Blocked", "SecurityError");
    });
    expect(readSearchOptions()).toEqual(DEFAULT_SEARCH_OPTIONS);
    expect(() => saveSearchOptions(DEFAULT_SEARCH_OPTIONS)).not.toThrow();
  });
});
