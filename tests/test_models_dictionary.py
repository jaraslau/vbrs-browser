"""Tests for the source dictionary Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.models.dictionary import Definition, DictionaryArticle

SAMPLE_ARTICLE: dict[str, object] = {
    "line": 10978,
    "raw": "ґадалІніюм, ґадалІн м. /gadalinijum, gadalin/ - гадолиний (Gd)",
    "word": "ґадалІніюм, ґадалІн",
    "be_notes": [],
    "gender": "м",
    "is_plural": False,
    "is_proper": False,
    "latin": "gadalinijum, gadalin",
    "is_link": False,
    "ru_notes": ["Gd"],
    "sources": [],
    "definitions": [{"number": None, "text": "гадолиний", "ru_notes": ["Gd"]}],
}


def test_full_article_parses() -> None:
    article = DictionaryArticle.model_validate(SAMPLE_ARTICLE)

    assert article.line == 10978
    assert article.raw.startswith("ґадалІніюм")
    assert article.word == "ґадалІніюм, ґадалІн"
    assert article.latin == "gadalinijum, gadalin"
    assert article.gender == "м"
    assert article.is_plural is False
    assert article.is_proper is False
    assert article.is_link is False
    assert article.be_notes == []
    assert article.ru_notes == ["Gd"]
    assert article.sources == []
    assert article.definitions == [
        Definition(number=None, text="гадолиний", ru_notes=["Gd"])
    ]


def test_optional_fields_default_when_missing() -> None:
    article = DictionaryArticle.model_validate(
        {"line": 1, "raw": "raw line", "word": "word", "latin": "latin"}
    )

    assert article.gender is None
    assert article.is_plural is False
    assert article.is_proper is False
    assert article.is_link is False
    assert article.be_notes == []
    assert article.ru_notes == []
    assert article.sources == []
    assert article.definitions == []


def test_required_fields_must_be_present() -> None:
    with pytest.raises(ValidationError):
        DictionaryArticle.model_validate(
            {"raw": "raw line", "word": "word", "latin": "latin"}
        )


def test_blank_word_rejected() -> None:
    with pytest.raises(ValidationError):
        DictionaryArticle.model_validate(
            {"line": 1, "raw": "raw line", "word": "   ", "latin": "latin"}
        )


def test_blank_raw_rejected() -> None:
    with pytest.raises(ValidationError):
        DictionaryArticle.model_validate(
            {"line": 1, "raw": "", "word": "word", "latin": "latin"}
        )


def test_definition_number_is_nullable() -> None:
    article = DictionaryArticle.model_validate(
        {
            **SAMPLE_ARTICLE,
            "definitions": [
                {"number": 1, "text": "першае значэнне"},
                {"number": None, "text": "другое значэнне"},
            ],
        }
    )

    assert article.definitions[0].number == 1
    assert article.definitions[1].number is None
    assert article.definitions[1].ru_notes == []


def test_definition_requires_text() -> None:
    with pytest.raises(ValidationError):
        Definition.model_validate({"number": 1, "ru_notes": []})


def test_definition_optional_fields_default_when_missing() -> None:
    definition = Definition.model_validate({"text": "толькі тэкст"})

    assert definition.number is None
    assert definition.ru_notes == []


def test_definition_unknown_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        Definition.model_validate({"text": "значэнне", "unexpected": True})


def test_wrong_types_rejected() -> None:
    with pytest.raises(ValidationError):
        DictionaryArticle.model_validate({**SAMPLE_ARTICLE, "line": "not-an-int"})
    with pytest.raises(ValidationError):
        DictionaryArticle.model_validate({**SAMPLE_ARTICLE, "is_plural": "yes"})
    with pytest.raises(ValidationError):
        DictionaryArticle.model_validate({**SAMPLE_ARTICLE, "gender": 5})


def test_unknown_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        DictionaryArticle.model_validate({**SAMPLE_ARTICLE, "unexpected": True})


def test_empty_gender_normalized_to_none() -> None:
    article = DictionaryArticle.model_validate({**SAMPLE_ARTICLE, "gender": "  "})

    assert article.gender is None


def test_model_dump_round_trip() -> None:
    article = DictionaryArticle.model_validate(SAMPLE_ARTICLE)

    assert DictionaryArticle.model_validate(article.model_dump()) == article