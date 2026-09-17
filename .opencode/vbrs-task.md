Build a production-quality web application named `vbrs-browser` for browsing and searching dictionary articles.

## Goal

The application is a read-only dictionary browser.

Dictionary data is supplied as one or more JSON files. A separate ingestion script must load those files into Elasticsearch. The web application must then allow users to search dictionary entries and view individual dictionary articles.

Keep the product deliberately simple. Do not introduce authentication, user accounts, editing, admin panels, relational databases, queues, or other infrastructure that is not required.

---

# Technology stack

Backend:

* Python
* FastAPI
* Pydantic / pydantic-settings
* Elasticsearch Python client
* Fully typed Python

Frontend:

* TypeScript
* React
* Use strict TypeScript configuration

Search/database:

* Elasticsearch

Runtime/containerization:

* Docker
* Separate frontend and backend services
* Multi-stage Docker builds

The repository must support local development with all required services, including Elasticsearch, through Docker Compose.

---

# Repository layout

Use this structure:

```text
vbrs-browser/
├── api/
│   ├── ...
│   └── ...
├── frontend/
│   ├── ...
│   └── ...
├── scripts/
│   └── ...
├── dockerfile.backend
├── dockerfile.frontend
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

Application source code must live under:

```text
vbrs-browser/api
vbrs-browser/frontend
```

The ingestion code may live under `scripts/` or under an appropriately named backend module with a thin script entrypoint.

Do not create a monolithic service. The frontend and backend must be independently buildable and runnable.

---

# Docker requirements

Create:

```text
dockerfile.backend
dockerfile.frontend
```

Use exactly those filenames.

Both Dockerfiles must use multi-stage builds.

The final runtime images should contain only what is required to run the application.

Provide `docker-compose.yml` containing at minimum:

* `backend`
* `frontend`
* `elasticsearch`

Services must communicate using Docker networking and configuration/environment variables rather than hardcoded hostnames scattered throughout the source code.

Add appropriate health checks where practical.

The backend must not assume Elasticsearch is immediately available at container startup.

---

# Configuration

`.env` must be ignored by Git from the beginning.

Provide:

```text
.env.example
```

It must be usable as a drop-in template:

```bash
cp .env.example .env
```

All environment-driven backend configuration must go through `pydantic-settings`.

Create a typed settings object and load configuration in one clearly defined place.

Configuration should cover, where applicable:

* backend host
* backend port
* frontend/backend public URLs if necessary
* CORS origins
* Elasticsearch URL
* Elasticsearch index name
* Elasticsearch connection settings
* request/search limits
* pagination defaults
* ingestion batch size
* logging level

Do not access environment variables ad hoc throughout the application.

Do not use unexplained magic numbers or duplicated hardcoded constants.

Values that represent configuration, limits, defaults, URLs, index names, timeouts, batch sizes, etc. should be defined centrally or provided through settings as appropriate.

---

# Python quality requirements

Python typing is mandatory.

Everything that reasonably has a type must be typed, including:

* function arguments
* return values
* class attributes
* collections
* local values where inference is insufficient
* Elasticsearch-facing DTOs
* ingestion structures

Avoid `Any` unless there is a concrete unavoidable reason.

Do not use untyped dictionaries as the application's domain model.

Use Pydantic models for external/request/response/data-boundary structures where appropriate.

Keep API models, application/domain logic, configuration, and Elasticsearch access separated.

Prefer small, composable modules rather than a single large `main.py`.

---

# TypeScript requirements

Enable strict TypeScript checking.

Avoid:

```ts
any
```

unless genuinely unavoidable.

Create explicit types/interfaces for:

* dictionary entries
* definitions
* API responses
* search responses
* pagination metadata
* API errors where applicable

Keep HTTP/API logic separate from presentation components.

---

# Input dictionary data

The ingestion process receives one or more JSON files.

Each file contains an array of dictionary article objects similar to:

```json
[
  {
    "line": 10978,
    "raw": "ґадалІніюм, ґадалІн м. /gadalinijum, gadalin/ - гадолиний (Gd)",
    "word": "ґадалІніюм, ґадалІн",
    "be_notes": [],
    "gender": "м",
    "is_plural": false,
    "is_proper": false,
    "latin": "gadalinijum, gadalin",
    "is_link": false,
    "ru_notes": [
      "Gd"
    ],
    "sources": [],
    "definitions": [
      {
        "number": null,
        "text": "гадолиний",
        "ru_notes": [
          "Gd"
        ]
      }
    ]
  },
  {
    "line": 11052,
    "raw": "ґазаахОўнік м. /gazaachoŭnik/ - противогаз (редкое)",
    "word": "ґазаахОўнік",
    "be_notes": [],
    "gender": "м",
    "is_plural": false,
    "is_proper": false,
    "latin": "gazaachoŭnik",
    "is_link": false,
    "ru_notes": [
      "редкое"
    ],
    "sources": [],
    "definitions": [
      {
        "number": null,
        "text": "противогаз",
        "ru_notes": [
          "редкое"
        ]
      }
    ]
  }
]
```

Model the schema explicitly.

At minimum, support:

```text
line
raw
word
be_notes
gender
is_plural
is_proper
latin
is_link
ru_notes
sources
definitions
```

A definition contains at minimum:

```text
number
text
ru_notes
```

Do not assume that all optional values are populated.

The importer should fail clearly on structurally invalid input rather than silently producing corrupted documents.

---

# Elasticsearch design

Elasticsearch is the application's database/search engine.

Create the index explicitly rather than relying on Elasticsearch dynamic mappings.

Define an appropriate mapping for every supported field.

The application primarily needs to search dictionary entries by:

1. `word`
2. `latin`
3. definition text
4. optionally the original `raw` field

Exact article data must still be retrievable without losing the original source fields.

Design analyzers/mappings so Cyrillic dictionary words and Latin transliterations can be searched effectively.

Do not implement language transformations that modify the source dictionary content.

Preserve the original values.

Search should be case-insensitive where practical.

Give `word` and `latin` higher relevance than definition text.

A sensible relevance order is:

```text
exact word match
prefix/close word match
latin match
definition match
raw-text match
```

Do not over-engineer search ranking.

---

# Stable document identity

Do not use Elasticsearch's automatically generated document ID if a deterministic identifier can be generated from the source data.

Generate a stable document identifier so repeated imports of the same dataset do not create duplicates.

The identifier must not depend on array position inside a particular ingestion run.

Document the chosen strategy.

---

# Ingestion script

Provide a command-line ingestion script capable of receiving multiple files, for example:

```bash
python -m scripts.import_dictionary data/file1.json data/file2.json
```

or an equivalent clean CLI.

It must:

1. load configuration using the same settings system as the backend where appropriate
2. validate input JSON
3. validate dictionary records against typed models
4. create the Elasticsearch index if necessary
5. optionally recreate the index through an explicit CLI flag
6. import records in batches
7. use Elasticsearch bulk indexing
8. report useful progress
9. report malformed records/files clearly
10. exit non-zero when ingestion fails

Support a flag similar to:

```text
--recreate-index
```

Do not delete an existing index during normal ingestion unless explicitly requested.

Repeated ingestion should be idempotent with respect to document identity.

Do not load every source file into one enormous in-memory structure if it can reasonably be processed file-by-file/batch-by-batch.

---

# Backend API

Expose a small REST API.

Use a versioned API prefix:

```text
/api/v1
```

At minimum implement:

```text
GET /api/v1/health
GET /api/v1/articles
GET /api/v1/articles/{article_id}
```

## Health endpoint

```text
GET /api/v1/health
```

Return service status and Elasticsearch connectivity status in a machine-readable form.

Do not expose credentials or internal configuration.

---

# Search endpoint

```text
GET /api/v1/articles
```

Support parameters such as:

```text
q
page
page_size
```

Example:

```text
GET /api/v1/articles?q=gadalin&page=1&page_size=20
```

The response should contain a stable structure similar to:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

Search must support queries against:

* `word`
* `latin`
* definition text

When `q` is missing or empty, return a deterministic paginated article listing rather than performing an invalid Elasticsearch query.

Validate page sizes and enforce a configurable maximum page size.

Do not expose raw Elasticsearch responses directly to the frontend.

Map Elasticsearch documents into explicit API response models.

---

# Article endpoint

```text
GET /api/v1/articles/{article_id}
```

Return the complete dictionary article.

Return a proper HTTP `404` response when the article does not exist.

API errors should use a consistent JSON shape.

---

# OpenAPI

FastAPI's generated OpenAPI documentation should remain enabled for development.

Use meaningful endpoint names, descriptions, models, and status codes so the generated API schema is useful.

---

# Backend architecture

Use a clean structure roughly equivalent to:

```text
api/
├── main.py
├── config/
├── models/
├── routers/
├── services/
├── repositories/
└── elasticsearch/
```

Exact names can vary when a better structure is justified.

Keep responsibilities separated:

```text
router
    ↓
service
    ↓
Elasticsearch repository/client
```

Do not put Elasticsearch query construction directly inside React code or FastAPI route handlers.

Do not introduce abstractions with no practical value, but keep the codebase maintainable.

---

# Frontend

Build a simple dictionary-browser UI.

The primary page should contain:

* application title
* search input
* search results
* loading state
* empty/no-results state
* API error state
* pagination when required

Each search result should make the dictionary headword prominent.

Display enough information to distinguish results, for example:

* `word`
* `latin`
* gender
* first definition or short definition summary

Selecting a result should show the complete article.

This can use either:

* a dedicated article route/page, or
* a detail panel

Prefer a dedicated route if it keeps browser navigation and sharing straightforward.

For example:

```text
/
/articles/:articleId
```

The article view should sensibly render:

* word
* latin form
* gender
* plural/proper-name flags when applicable
* Belarusian notes
* Russian notes
* definitions
* definition numbers
* definition notes
* sources
* original/raw article text where useful

Do not make the UI visually elaborate. Optimize for readability and fast dictionary lookup.

---

# Search UX

Do not make a backend request on every keystroke without control.

Use either:

* submit-based search, or
* a small configurable debounce

Search state should be represented in the URL where practical, e.g.:

```text
/?q=gadalin&page=1
```

This allows search results to be bookmarked and browser navigation to work naturally.

Handle Unicode correctly throughout the frontend/backend stack.

---

# Frontend/backend communication

The frontend API base URL must be configuration-driven.

Do not hardcode values such as:

```text
http://localhost:8000
```

inside application components.

For Docker production-style deployment, expose the required configuration cleanly.

Configure CORS explicitly on the backend.

Do not use `*` as the production CORS configuration unless there is a documented reason.

---

# Error handling

Handle expected Elasticsearch failures.

Backend errors should be logged with useful context without leaking sensitive information to clients.

The frontend must distinguish:

* loading
* no results
* backend unavailable/error
* successful results

Avoid swallowing exceptions.

---

# Logging

Use Python logging rather than `print()` for backend runtime logging.

The ingestion CLI may print human-readable progress, but important failures should also be logged appropriately.

Logging verbosity should be configurable.

---

# Testing

Provide meaningful automated tests.

Backend tests should cover at least:

* settings/configuration behavior
* Pydantic validation of dictionary records
* article response serialization
* search parameter validation
* health endpoint behavior
* article-not-found behavior
* repository/service behavior with Elasticsearch mocked or isolated appropriately
* stable document ID generation

Frontend tests should cover at least:

* search form behavior
* result rendering
* loading/error/empty states
* article rendering

Tests must not depend on a public Elasticsearch service.

If integration tests requiring Elasticsearch are added, separate them clearly from normal unit tests.

---

# Code quality

Backend should include appropriate static checks such as:

```text
ruff
mypy or pyright
pytest
```

Configure strict enough type checking to catch meaningful errors.

Frontend should include:

```text
eslint
TypeScript typecheck
frontend test runner
```

Provide package/project scripts or documented commands for running all checks.

Generated code should pass its own configured linters, tests, and type checking.

Do not leave placeholder TODOs for core functionality.

---

# README

Write a useful `README.md` explaining:

1. what the application does
2. project architecture
3. requirements
4. environment configuration
5. how to create `.env`
6. how to run locally with Docker Compose
7. how to run frontend/backend separately for development
8. how Elasticsearch is configured
9. how to ingest dictionary files
10. how to recreate the index
11. API endpoints
12. how to run tests
13. how to run linters/type checks
14. relevant architectural decisions

A new developer should be able to clone the project, copy `.env.example`, start the stack, ingest JSON files, and use the dictionary browser without reverse-engineering the repository.

---

# Expected basic workflow

The resulting project should support approximately:

```bash
git clone ...
cd vbrs-browser

cp .env.example .env

docker compose up --build -d
```

Then dictionary data can be imported using a documented command, for example:

```bash
docker compose exec backend \
  python -m scripts.import_dictionary \
  /data/dictionary-1.json \
  /data/dictionary-2.json
```

The exact command can differ if the architecture warrants it, but the workflow must be straightforward and documented.

---

# Environment hygiene

`.gitignore` must include at minimum:

```text
.env
.env.*
!.env.example
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
node_modules/
dist/
build/
coverage/
```

Add other generated IDE/build/runtime files as appropriate.

Never commit secrets.

Do not include real credentials in `.env.example`.

---

# Non-goals

Do not implement:

* authentication
* authorization
* dictionary editing
* user accounts
* admin UI
* PostgreSQL/MySQL
* Redis
* message queues
* server-side rendered React unless genuinely necessary
* analytics
* telemetry
* external SaaS dependencies
* unnecessary microservices

There should be one frontend application, one backend application, and Elasticsearch.

---

# Implementation principles

Prefer:

* boring, maintainable solutions
* explicit schemas
* strict typing
* deterministic behavior
* dependency injection where it materially improves testing
* small modules
* configuration over hardcoding
* clear failure modes

Avoid:

* premature abstractions
* hidden global state
* magic numbers
* implicit configuration
* untyped data structures
* leaking Elasticsearch-specific response formats into the frontend
* unnecessary dependencies

---

# Acceptance criteria

The implementation is complete when all of the following are true:

1. `dockerfile.backend` exists and uses a multi-stage build.
2. `dockerfile.frontend` exists and uses a multi-stage build.
3. Frontend and backend are separate services.
4. Elasticsearch runs as a separate service.
5. `.env` is gitignored.
6. `.env.example` contains every required environment variable.
7. Backend configuration uses `pydantic-settings`.
8. Python code is comprehensively typed.
9. TypeScript uses strict typing.
10. Elasticsearch mappings are explicitly defined.
11. Multiple dictionary JSON files can be imported.
12. Import uses bulk indexing.
13. Reimporting data does not create uncontrolled duplicates.
14. Search works across `word`, `latin`, and definition text.
15. Results are paginated.
16. A complete article can be retrieved by ID.
17. The frontend can search and display articles.
18. Loading, empty, and error states are implemented.
19. Configuration and limits are not scattered as magic constants.
20. Backend tests pass.
21. Frontend tests pass.
22. Backend linting and type checking pass.
23. Frontend linting and type checking pass.
24. The application can be started following only the README.
25. There are no placeholder implementations for required functionality.

Before considering the task finished, run the project's tests, linters, and type checks and fix issues discovered by them.

Where a minor implementation detail is unspecified, choose the simplest maintainable solution consistent with the requirements above and document any consequential architectural choice in the README.
