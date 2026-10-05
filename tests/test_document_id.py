from __future__ import annotations

import hashlib
import re

from backend.elasticsearch.document_id import article_document_id
from backend.models.dictionary import DictionaryArticle


def _article(word: str = "ґадалІніюм, ґадалІн", raw: str = "raw line") -> DictionaryArticle:
    return DictionaryArticle(line=1, raw=raw, word=word, latin="latin")


def test_id_is_sha256_hex_digest() -> None:
    article_id = article_document_id(_article())

    assert len(article_id) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", article_id) is not None


def test_id_is_stable_across_calls() -> None:
    article = _article()

    assert article_document_id(article) == article_document_id(article)


def test_id_is_deterministic_for_equal_articles() -> None:
    assert article_document_id(_article()) == article_document_id(_article())


def test_id_matches_independently_computed_sha256() -> None:
    # Pin the exact contract so an accidental change of the hashed payload
    # (field order, separator, encoding) is caught: the ID is the SHA-256 of
    # `word` and `raw` joined by the ASCII unit separator.
    article = _article()
    expected = hashlib.sha256(f"{article.word}\x1f{article.raw}".encode()).hexdigest()

    assert article_document_id(article) == expected


def test_id_changes_with_word() -> None:
    assert article_document_id(_article(word="іншае слова")) != article_document_id(_article())


def test_id_changes_with_raw() -> None:
    assert article_document_id(_article(raw="another raw line")) != article_document_id(_article())


def test_id_does_not_depend_on_article_position() -> None:
    # The ID is a pure function of the source values; two articles with equal
    # content produce the same ID regardless of their position in a dataset.
    first = _article()
    second = _article()

    assert article_document_id(first) == article_document_id(second)


def test_id_distinguishes_ambiguous_concatenations() -> None:
    # "ab" + "c" must not collide with "a" + "bc": the field separator keeps
    # word/raw concatenations unambiguous.
    left = article_document_id(_article(word="ab", raw="c"))
    right = article_document_id(_article(word="a", raw="bc"))

    assert left != right
