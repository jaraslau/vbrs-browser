"""Tests for deterministic document ID generation."""

from __future__ import annotations

import re

from api.elasticsearch.document_id import article_document_id
from api.models.dictionary import DictionaryArticle


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


def test_id_changes_with_word() -> None:
    assert article_document_id(_article(word="іншае слова")) != article_document_id(
        _article()
    )


def test_id_changes_with_raw() -> None:
    assert article_document_id(_article(raw="another raw line")) != article_document_id(
        _article()
    )


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