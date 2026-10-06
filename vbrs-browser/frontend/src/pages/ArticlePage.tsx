import { Link, useParams } from "react-router-dom";

import type { Article } from "../api/types";
import { LoadingMessage, ErrorMessage } from "../components/StatusMessage";
import { useArticle } from "../hooks/useArticles";

/**
 * Article detail page: renders the complete dictionary article addressed by
 * the ``:articleId`` route parameter.
 */
export function ArticlePage({ embedded = false }: { embedded?: boolean }) {
  const params = useParams<{ articleId: string }>();
  const articleId = params.articleId ?? "";
  const request = useArticle(articleId);

  if (request.status === "loading") {
    return <LoadingMessage />;
  }

  if (request.status === "error") {
    if (request.notFound) {
      return (
        <section className="not-found">
          <h2>Article not found</h2>
          <p>{request.message}</p>
          {!embedded && <Link to="/">Back to search</Link>}
        </section>
      );
    }
    return <ErrorMessage message={request.message} onRetry={request.retry} />;
  }

  return (
    <>
      {!embedded && (
        <Link to="/" className="back-link">
          ← Back to search
        </Link>
      )}
      <ArticleDetail article={request.article} />
    </>
  );
}

/** The full article body: every dictionary field, laid out for reading. */
export function ArticleDetail({ article }: { article: Article }) {
  return (
    <article className="article-detail" aria-labelledby="article-headword">
      <p className="eyebrow">Dictionary / Entry {article.line}</p>
      <h2 id="article-headword" className="article-word">
        {article.word}
      </h2>

      <dl className="article-meta">
        {article.latin !== "" && (
          <>
            <dt>Latin</dt>
            <dd>{article.latin}</dd>
          </>
        )}
        {article.gender !== null && (
          <>
            <dt>Gender</dt>
            <dd>{article.gender}</dd>
          </>
        )}
        <dt>Line</dt>
        <dd>{article.line}</dd>
      </dl>

      <ArticleFlags article={article} />

      <NotesSection title="Belarusian notes" notes={article.be_notes} />
      <NotesSection title="Russian notes" notes={article.ru_notes} />

      <DefinitionsList article={article} />

      <SourcesList sources={article.sources} />

      <section className="article-raw">
        <h3>Original text</h3>
        <pre>{article.raw}</pre>
      </section>
    </article>
  );
}

/** Plural/proper/link flags, rendered only when applicable. */
function ArticleFlags({ article }: { article: Article }) {
  const flags: string[] = [];
  if (article.is_plural) {
    flags.push("plural");
  }
  if (article.is_proper) {
    flags.push("proper name");
  }
  if (article.is_link) {
    flags.push("link");
  }
  if (flags.length === 0) {
    return null;
  }
  return (
    <ul className="article-flags" aria-label="Article flags">
      {flags.map((flag) => (
        <li key={flag}>{flag}</li>
      ))}
    </ul>
  );
}

/** A heading plus a list of notes, hidden entirely when there are none. */
function NotesSection({ title, notes }: { title: string; notes: string[] }) {
  if (notes.length === 0) {
    return null;
  }
  return (
    <section className="article-notes">
      <h3>{title}</h3>
      <ul>
        {notes.map((note, index) => (
          <li key={index}>{note}</li>
        ))}
      </ul>
    </section>
  );
}

/** Numbered list of definitions with their per-sense notes. */
function DefinitionsList({ article }: { article: Article }) {
  if (article.definitions.length === 0) {
    return null;
  }
  return (
    <section className="article-definitions">
      <h3>Definitions</h3>
      <ol>
        {article.definitions.map((definition, index) => (
          <li key={index} className="definition">
            <p className="definition-body">
              {definition.number !== null && (
                <span className="definition-number">{definition.number}.</span>
              )}
              <span className="definition-text">{definition.text}</span>
            </p>
            {definition.ru_notes.length > 0 && (
              <ul className="definition-notes">
                {definition.ru_notes.map((note, noteIndex) => (
                  <li key={noteIndex}>{note}</li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

/** Source references, hidden entirely when there are none. */
function SourcesList({ sources }: { sources: string[] }) {
  if (sources.length === 0) {
    return null;
  }
  return (
    <section className="article-sources">
      <h3>Sources</h3>
      <ul>
        {sources.map((source, index) => (
          <li key={index}>{source}</li>
        ))}
      </ul>
    </section>
  );
}
