/**
 * Typed contracts for the vbrs-browser API.
 *
 * These mirror the Pydantic response models exposed by the backend under
 * ``/api/v1`` (see ``api/models/api.py`` and ``api/models/dictionary.py``).
 * The shapes are explicit so the rest of the application never deals with
 * untyped JSON.
 */

/** A single sense/meaning of a dictionary article. */
export interface Definition {
  /** Sense number within the article, when the source provides one. */
  number: number | null;
  /** Definition text. */
  text: string;
  /** Russian-language notes attached to this sense. */
  ru_notes: string[];
}

/** A complete dictionary article, including its stable document ID. */
export interface Article {
  /** Stable Elasticsearch document ID used to address the article. */
  id: string;
  /** Source line number inside the dictionary data file. */
  line: number;
  /** Original, unprocessed article text from the source data. */
  raw: string;
  /** Dictionary headword. */
  word: string;
  /** Latin transliteration of the headword. */
  latin: string;
  /** Grammatical gender, when the source provides one. */
  gender: string | null;
  /** True when the article is a plural-only form. */
  is_plural: boolean;
  /** True when the article is a proper name. */
  is_proper: boolean;
  /** True when the article is a cross-reference link. */
  is_link: boolean;
  /** Belarusian-language notes attached to the article. */
  be_notes: string[];
  /** Russian-language notes attached to the article. */
  ru_notes: string[];
  /** Source references cited by the article. */
  sources: string[];
  /** The senses/meanings of the article. */
  definitions: Definition[];
}

/** Paginated response for ``GET /api/v1/articles``. */
export interface ArticleListResponse {
  /** Articles on the requested page. */
  items: Article[];
  /** 1-based page number of the returned items. */
  page: number;
  /** Number of items requested per page. */
  page_size: number;
  /** Total number of matching articles across all pages. */
  total: number;
}

/** JSON error payload returned for failed API requests. */
export interface ApiErrorResponse {
  detail: string;
}