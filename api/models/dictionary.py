"""Pydantic models describing source dictionary articles.

These models mirror the JSON schema of the dictionary data files supplied to
the ingestion pipeline. They are intentionally strict: unknown fields and
structurally invalid values fail validation so the importer rejects bad input
instead of silently indexing corrupted documents.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Definition(BaseModel):
    """A single sense/meaning of a dictionary article.

    Attributes:
        number: Sense number within the article, when the source provides one.
        text: Definition text.
        ru_notes: Russian-language notes attached to this sense.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    number: int | None = None
    text: str
    ru_notes: list[str] = Field(default_factory=list)


class DictionaryArticle(BaseModel):
    """A complete dictionary article as provided by a source data file.

    Every field mirrors an attribute of the source JSON schema. Only
    ``line``, ``raw``, ``word`` and ``latin`` are required; all remaining
    fields default to a neutral value when absent from the source data.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    line: int
    raw: str
    word: str
    latin: str
    gender: str | None = None
    is_plural: bool = False
    is_proper: bool = False
    is_link: bool = False
    be_notes: list[str] = Field(default_factory=list)
    ru_notes: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    definitions: list[Definition] = Field(default_factory=list)

    @field_validator("word", "raw")
    @classmethod
    def _ensure_not_blank(cls, value: str) -> str:
        """Headwords and raw lines must not be blank."""
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("gender")
    @classmethod
    def _normalize_gender(cls, value: str | None) -> str | None:
        """Coerce whitespace-only gender values to None."""
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None