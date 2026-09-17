import type { Article } from "../api/types";

export function firstDefinitionText(article: Article): string | null {
  const first = article.definitions[0];
  return first === undefined ? null : first.text;
}