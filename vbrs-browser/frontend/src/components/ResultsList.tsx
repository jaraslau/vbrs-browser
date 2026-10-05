import { Link } from "react-router-dom";

import type { Article } from "../api/types";
import { firstDefinitionText } from "../lib/article";

/**
 * A single search result linking to the full article.
 *
 * The headword is prominent; the Latin transliteration, gender, and first
 * definition are shown so results can be distinguished at a glance.
 */
function ResultItem({ article }: { article: Article }) {
  const definition = firstDefinitionText(article);
  return (
    <li className="result-item">
      <Link to={`/articles/${encodeURIComponent(article.id)}`} className="result-link">
        <span className="result-word">{article.word}</span>
        {article.latin !== "" && (
          <span className="result-latin">{article.latin}</span>
        )}
        {article.gender !== null && (
          <span className="result-gender">{article.gender}</span>
        )}
      </Link>
      {definition !== null && (
        <p className="result-definition">{definition}</p>
      )}
    </li>
  );
}

export function ResultsList({ articles }: { articles: Article[] }) {
  if (articles.length === 0) {
    return null;
  }
  return (
    <ol className="results-list" aria-label="Search results">
      {articles.map((article) => (
        <ResultItem key={article.id} article={article} />
      ))}
    </ol>
  );
}