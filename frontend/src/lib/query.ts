/**
 * Parse a query-string value as a base-10 integer, falling back to
 * ``fallback`` when the value is missing or not a valid number.
 */
export function parsePositiveInt(value: string | null, fallback: number): number {
  if (value === null) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isInteger(parsed) && parsed >= 1 ? parsed : fallback;
}