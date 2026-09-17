/**
 * Pagination helpers shared by the search page and its tests.
 */

/** A page number in the window, or a gap marker rendered as an ellipsis. */
export type PageWindowEntry = number | "ellipsis";

/**
 * Build the ordered list of page numbers to show in a pager.
 *
 * Returns an empty array when there is nothing to paginate. The window
 * always includes the first and last pages plus up to ``radius`` pages on
 * each side of the current page, with ``"ellipsis"`` gap markers in between.
 *
 * @param current 1-based current page.
 * @param totalPages Total number of pages (>= 1).
 * @param radius How many pages to show on each side of the current page.
 */
export function buildPageWindow(
  current: number,
  totalPages: number,
  radius = 2,
): PageWindowEntry[] {
  if (totalPages <= 1) {
    return [];
  }

  const pages = new Set<number>([1, totalPages]);
  for (let page = current - radius; page <= current + radius; page += 1) {
    if (page >= 1 && page <= totalPages) {
      pages.add(page);
    }
  }

  const sorted = [...pages].sort((a, b) => a - b);
  const window: PageWindowEntry[] = [];
  let previous = 0;
  for (const page of sorted) {
    if (page - previous > 1) {
      window.push("ellipsis");
    }
    window.push(page);
    previous = page;
  }
  return window;
}

/** Total number of pages for a result set, clamped to at least 1. */
export function totalPages(pageSize: number, total: number): number {
  if (pageSize < 1) {
    return 1;
  }
  return Math.max(1, Math.ceil(total / pageSize));
}