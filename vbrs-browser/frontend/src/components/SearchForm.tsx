import { useEffect, useState } from "react";
import type { FormEvent } from "react";

/**
 * The search input and submit button.
 *
 * Submit-based search by design: the query is only sent to the API when the
 * form is submitted, never on every keystroke. The input is kept in sync
 * with the URL-derived query so browser navigation updates it too.
 */
export function SearchForm({
  defaultQuery,
  onSearch,
}: {
  defaultQuery: string;
  onSearch: (query: string) => void;
}) {
  const [value, setValue] = useState(defaultQuery);

  useEffect(() => {
    setValue(defaultQuery);
  }, [defaultQuery]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
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
        onChange={(event) => setValue(event.target.value)}
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
