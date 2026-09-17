import { buildPageWindow, totalPages } from "../lib/pagination";

/**
 * Page-number navigation for a paginated result set.
 *
 * Renders Previous/Next buttons and a numbered window around the current
 * page. Disabled buttons and a visible ``aria-current`` marker communicate
 * the current position. Renders nothing when there is only one page.
 */
export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}) {
  const count = totalPages(pageSize, total);
  if (count <= 1) {
    return null;
  }

  const window = buildPageWindow(page, count);
  const canGoPrevious = page > 1;
  const canGoNext = page < count;

  return (
    <nav className="pagination" aria-label="Pagination">
      <button
        type="button"
        className="pagination-prev"
        disabled={!canGoPrevious}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </button>
      <ul className="pagination-pages">
        {window.map((entry, index) => {
          if (entry === "ellipsis") {
            return (
              <li key={`gap-${index}`} className="pagination-gap" aria-hidden="true">
                …
              </li>
            );
          }
          const isCurrent = entry === page;
          return (
            <li key={entry}>
              <button
                type="button"
                className="pagination-page"
                aria-current={isCurrent ? "page" : undefined}
                onClick={() => onPageChange(entry)}
              >
                {entry}
              </button>
            </li>
          );
        })}
      </ul>
      <button
        type="button"
        className="pagination-next"
        disabled={!canGoNext}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </button>
    </nav>
  );
}