import type { Article } from "../api/types";

/** Text of the first definition of an article, when it has one. */
export function firstDefinitionText(article: Article): string | null {
  const first = article.definitions[0];
  return first === undefined ? null : first.text;
}