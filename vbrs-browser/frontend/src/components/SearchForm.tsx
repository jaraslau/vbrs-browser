import { useEffect, useState } from "react";
import type { FormEvent } from "react";

/**
 * The search input and submit button.
 *
 * Submission updates the full results; preview changes leave the URL alone.
 */
export function SearchForm({
  defaultQuery,
  onSearch,
  onPreview,
}: {
  defaultQuery: string;
  onSearch: (query: string) => void;
  onPreview?: (query: string | null) => void;
}) {
  const [value, setValue] = useState(defaultQuery);

  useEffect(() => {
    setValue(defaultQuery);
    onPreview?.(null);
  }, [defaultQuery, onPreview]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onPreview?.(null);
    onSearch(value.trim());
  };

  return (
    <form role="search" className="search-form" onSubmit={handleSubmit}>
      <label className="sr-only" htmlFor="search-input">
        Search
      </label>
      <svg
        className="search-icon"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 5 5" />
      </svg>
      <input
        id="search-input"
        type="search"
        value={value}
        placeholder="Search for a word…"
        autoComplete="off"
        aria-describedby="search-hint"
        onFocus={() => onPreview?.(value.trim())}
        onChange={(event) => {
          setValue(event.target.value);
          onPreview?.(event.target.value.trim());
        }}
      />
      <button type="submit">
        <span className="sr-only">Search</span>
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M4 12h16m-6-6 6 6-6 6" />
        </svg>
      </button>
      <p id="search-hint" className="search-hint">
        Search in Cyrillic or Latin. Leave blank to explore all entries.
      </p>
    </form>
  );
}
