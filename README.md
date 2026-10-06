# vbrs-browser

A read-only dictionary browser: search dictionary articles and view individual
entries. Dictionary data is supplied as JSON files and imported into
Elasticsearch; the web application searches and displays the articles.

## Status

The repository layout, configuration, container definitions, ingestion
pipeline, and tooling are in place. The FastAPI backend exposes the health,
article search, and article detail endpoints under `/api/v1`; the React/TypeScript
frontend implements URL-synced search with pagination, debounced live word
previews, and article modals that preserve the search underneath. Direct
article URLs also render as standalone pages. Live previews reuse the HTTP
search API, cancel superseded requests, and leave the submitted query unchanged.

## Architecture

- **Backend** (`vbrs-browser/backend/`) — Python / FastAPI, importable as the
  top-level `backend` package. Fully typed; configuration is centralized in
  `backend/config/settings.py` via `pydantic-settings`.
  - `backend/config/` — typed settings (env-driven, `.env` supported)
  - `backend/models/` — Pydantic models for dictionary data and API boundaries
  - `backend/routers/`, `backend/services/`, `backend/repositories/` — route/
    service/repository layers
  - `backend/elasticsearch/` — Elasticsearch client access and query construction
- **Frontend** (`vbrs-browser/frontend/`) — TypeScript / React (strict mode)
  built with Vite. API access is same-origin through `/api` (proxied by the
  Vite dev server and by nginx in production); no backend URLs are hardcoded
  in components.
- **Ingestion** (`vbrs-browser/scripts/`) — command-line importer
  (`python -m scripts.import_dictionary ...`), plus the container entrypoint.
- **Search/database** — Elasticsearch single node via Docker Compose.

## Repository layout

```
<repo-root>/
├── vbrs-browser/            # application source
│   ├── backend/             # FastAPI service (package `backend`)
│   ├── frontend/            # React/Vite single-page app
│   └── scripts/             # ingestion CLI + container entrypoint
├── tests/                   # backend test suite
├── dockerfile.backend
├── dockerfile.frontend
├── docker-compose.yml
├── .env.example             # copy to .env; single source of truth for config
└── pyproject.toml
```

## Requirements

- Docker with the Compose plugin (recommended path)
- Python 3.11+ and Node.js 22+ for running services outside Docker
- Elasticsearch 8.x (provided by Docker Compose)

## Environment configuration

Copy `.env.example` to `.env` and adjust values as needed:

```bash
cp .env.example .env
```

`.env` is the single source of truth for environment-variable values and is
gitignored. Docker Compose consumes it both for interpolation and via
`env_file`, so no value is restated in `docker-compose.yml`. Application
settings flow through `vbrs-browser/backend/config/settings.py`.

`.env.example` documents each variable's consumer. Most are application
settings; a few exist only for Compose wiring (`FRONTEND_PORT`,
`ES_PUBLIC_PORT`, `BACKEND_INTERNAL_URL`, `DICTIONARY_SOURCE_DIR`) and one for
the container entrypoint (`DICTIONARY_IMPORT_DIR`).

## Running with Docker Compose

```bash
cp .env.example .env
docker compose up --build -d
```

Services:

| Service        | URL                         |
| -------------- | --------------------------- |
| elasticsearch  | http://localhost:9200       |
| backend API    | http://localhost:8000       |
| frontend       | http://localhost:8080       |
| OpenAPI docs   | http://localhost:8000/docs  |

All services define health checks; `backend` and `frontend` wait for their
dependencies to become healthy. The backend starts even when Elasticsearch is
unavailable and reports connectivity through the health endpoint.

Both application containers run as dedicated unprivileged users, drop all
Linux capabilities, and set `no-new-privileges`. Neither needs to bind a
privileged port. The backend runs with a read-only root filesystem; the
frontend keeps a writable path only where the nginx entrypoint renders its
configuration, with `/tmp` mounted as an explicit tmpfs.

## Running frontend/backend separately (development)

Backend:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
uvicorn backend.main:app --reload
```

Frontend (Vite dev server proxies `/api` to the backend at
`VITE_BACKEND_URL`, default `http://localhost:8000`):

```bash
cd vbrs-browser/frontend
cp .env.example .env   # optional
npm install
npm run dev            # http://localhost:5173
```

## Elasticsearch

Compose starts a single-node Elasticsearch 8 cluster with security disabled
for local development and persists its data in the `elasticsearch_data`
volume. The backend connects to `http://elasticsearch:9200` inside the
Compose network (override via `ES_URL` in the backend service environment)
and to `http://localhost:9200` when run locally (from `.env`).

Explicit index mappings are defined in
`vbrs-browser/backend/elasticsearch/mappings.py` and applied by the ingestion
pipeline.

### Schema management

This project has no relational database, so Alembic does not apply. The chosen
schema-management mechanism is the explicit, version-controlled index mapping
plus the data-and-schema fingerprint described below:

- the mapping is declared in code (`INDEX_MAPPING` / `INDEX_SETTINGS`), never
  inferred from dynamic mapping (`dynamic: strict`);
- the fingerprint covers both the input data **and** the mapping itself, so any
  schema or data change is detected and the index is recreated;
- the index is only ever created or replaced by the ingestion command, never
  implicitly at application startup — the served application is read-only.

Recreating the index is destructive, so it is always performed by the explicit
importer rather than by a migration step applied automatically on every boot.

## Ingestion

`vbrs-browser/scripts/backend_entrypoint.sh` imports the JSON files mounted at
`DICTIONARY_IMPORT_DIR` before the server starts. The importer computes a
data-and-schema fingerprint stored in the Elasticsearch mapping, which skips
an unchanged dataset; changed data is validated in full before the index is
recreated and imported, so invalid input cannot replace the last good index and
removed articles do not linger. `sayings.json` is excluded because it uses a
separate source schema from dictionary articles.

The import runs from the container entrypoint, which is safe here because
Compose runs a single backend replica. A multi-replica or orchestrated
deployment must move this step into a dedicated release job so replicas do not
race to recreate the index.

Dictionary JSON files can also be imported manually in batches:

```bash
docker compose exec backend \
  python -m scripts.import_dictionary /data/dictionary/*.json
```

Documents receive a stable, deterministic identifier so repeated imports do
not create duplicates. Pass `--if-changed` to skip an identical dataset and
recreate the index when it differs, or `--recreate-index` to recreate it
unconditionally. Import failures exit with a non-zero status.

## API endpoints

| Method | Path                  | Description                             |
| ------ | --------------------- | --------------------------------------- |
| GET    | `/api/v1/health`      | Service and Elasticsearch connectivity  |
| GET    | `/api/v1/articles`    | Paginated search / listing              |
| GET    | `/api/v1/articles/{article_id}` | Full dictionary article      |

Behavior notes:

* `GET /api/v1/articles` accepts `q`, `page` (1-based) and `page_size`
  query parameters. When `q` is missing or blank the endpoint returns a
  deterministic paginated listing of all articles. `page_size` defaults to
  the configured `page_size` value and is clamped to `max_page_size`; the
  effective value is echoed back in the response.
  Nonblank queries match the beginning of the full headword or transliteration,
  case-insensitively; later words, definitions, and raw article text do not match.
  This applies to both live previews and submitted searches.
* `GET /api/v1/articles/{article_id}` returns 404 with a JSON error body when
  the article does not exist.
* All errors use the same JSON shape (`{"detail": ...}`) as FastAPI's
  validation errors. Elasticsearch failures are logged server-side and
  reduced to client-safe 5xx messages; raw Elasticsearch responses are never
  exposed to the frontend.
* `GET /api/v1/health` always answers 200 while the process is up; read the
  `elasticsearch` field to tell a degraded service from a dead process.

Interactive OpenAPI documentation is enabled for development.

## Tests

Backend:

```bash
pip install -e ".[dev]"
pytest
```

Frontend:

```bash
cd vbrs-browser/frontend
npm test
```

## Linters and type checks

Backend:

```bash
ruff check .
mypy
```

Frontend:

```bash
cd vbrs-browser/frontend
npm run typecheck
npm run lint
```

## License

MIT — see `license`.
