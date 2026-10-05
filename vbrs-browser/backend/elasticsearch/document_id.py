"""Deterministic Elasticsearch document identity for dictionary articles.

Repeated imports of the same source data must not create duplicate documents.
Instead of relying on Elasticsearch's auto-generated IDs, every article is
addressed by a SHA-256 digest computed from its source values, so the same
source line always maps to the same document ID and re-importing simply
updates the existing document.
"""

from __future__ import annotations

import hashlib

from backend.models.dictionary import DictionaryArticle

# ASCII unit separator (U+001F). Joining `word` and `raw` with a control
# character that cannot occur in dictionary text prevents ambiguous
# concatenations such as ("ab", "c") vs ("a", "bc") from colliding.
_FIELD_SEPARATOR = "\x1f"


def article_document_id(article: DictionaryArticle) -> str:
    """Return the stable Elasticsearch document ID for a dictionary article.

    The ID is the hex SHA-256 digest of ``word`` and ``raw`` (UTF-8 encoded)
    separated by an ASCII unit separator. Because both values are taken
    verbatim from the source record, the ID:

    * is stable across ingestion runs of the same dataset,
    * does not depend on array position or file ordering,
    * changes whenever the source headword or raw line changes.
    """
    payload = f"{article.word}{_FIELD_SEPARATOR}{article.raw}".encode()
    return hashlib.sha256(payload).hexdigest()
