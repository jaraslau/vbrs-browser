import { Link, useLocation } from "react-router-dom";

import type { Article } from "../api/types";
import { firstDefinitionText } from "../lib/article";

function ResultItem({ article }: { article: Article }) {
  const location = useLocation();
  const definition = firstDefinitionText(article);
  return (
    <li className="result-item">
      <Link
        to={`/articles/${encodeURIComponent(article.id)}`}
        state={{ backgroundLocation: location }}
        className="result-link"
      >
        <span className="result-line" aria-hidden="true">
          {String(article.line).padStart(5, "0")}
        </span>
        <span className="result-body">
          <span className="result-word">{article.word}</span>
          {(article.latin !== "" || article.gender !== null) && (
            <span className="result-meta">
              {article.latin !== "" && (
                <span className="result-latin">{article.latin}</span>
              )}
              {article.gender !== null && (
                <span className="result-gender">{article.gender}</span>
              )}
            </span>
          )}
          {definition !== null && (
            <span className="result-definition">{definition}</span>
          )}
        </span>
        <span className="result-arrow" aria-hidden="true">
          ↗
        </span>
      </Link>
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
