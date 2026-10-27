import { DEFAULT_SEARCH_OPTIONS, SEARCH_OPTIONS_STORAGE_KEY } from "../config";

export type SearchOptions = typeof DEFAULT_SEARCH_OPTIONS;

export function normalizeSearchQuery(
  query: string,
  options: SearchOptions,
): string {
  let normalized = query;
  if (options.latinI) {
    normalized = normalized.replace(
      /(?<=\p{Script=Cyrillic})[iI]/gu,
      (letter) => (letter === "I" ? "І" : "і"),
    );
  }
  if (options.cyrillicI) {
    normalized = normalized.replace(/[иИ]/g, (letter) =>
      letter === "И" ? "І" : "і",
    );
  }
  if (options.shortU) {
    normalized = normalized.replace(/(?<=[аоуеюёАОУЕЮЁ])[уУ]/g, (letter) =>
      letter === "У" ? "Ў" : "ў",
    );
  }
  return normalized;
}

export function readSearchOptions(): SearchOptions {
  try {
    const stored: unknown = JSON.parse(
      window.localStorage.getItem(SEARCH_OPTIONS_STORAGE_KEY) ?? "null",
    );
    if (typeof stored === "object" && stored !== null) {
      return {
        latinI: "latinI" in stored && stored.latinI === true,
        cyrillicI: "cyrillicI" in stored && stored.cyrillicI === true,
        shortU: "shortU" in stored && stored.shortU === true,
      };
    }
  } catch {
    // Storage can be unavailable or contain invalid data; keep search usable.
  }
  return { ...DEFAULT_SEARCH_OPTIONS };
}

export function saveSearchOptions(options: SearchOptions): void {
  try {
    window.localStorage.setItem(
      SEARCH_OPTIONS_STORAGE_KEY,
      JSON.stringify(options),
    );
  } catch {
    // Blocked storage must not prevent changing options for this session.
  }
}
