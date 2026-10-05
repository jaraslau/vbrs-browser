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
      <label htmlFor="search-input">Search</label>
      <input
        id="search-input"
        type="search"
        value={value}
        placeholder="e.g. gadalinium"
        autoComplete="off"
        onChange={(event) => setValue(event.target.value)}
      />
      <button type="submit">Search</button>
    </form>
  );
}