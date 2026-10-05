# vbrs-browser

A read-only dictionary browser: search dictionary articles and view individual
entries. Dictionary data is supplied as JSON files and imported into
Elasticsearch; the web application searches and displays the articles.

## Status

The repository layout, configuration, container definitions, ingestion
pipeline, and tooling are in place. The FastAPI backend exposes the health,
article search, and article detail endpoints under `/api/v1`; the React/TypeScript
frontend implements the search page (URL-synced, submit-based search with
pagination) and the article detail route on top of them.

## Architecture

- **Backend** (`api/`) — Python / FastAPI. Fully typed; configuration is
  centralized in `api/config/settings.py` via `pydantic-settings`.
  - `api/config/` — typed settings (env-driven, `.env` supported)
  - `api/models/` — Pydantic models for dictionary data and API boundaries
  - `api/routers/`, `api/services/`, `api/repositories/` — route/service/
    repository layers
  - `api/elasticsearch/` — Elasticsearch client access and query construction
- **Frontend** (`frontend/`) — TypeScript / React (strict mode) built with Vite.
  API access is same-origin through `/api` (proxied by the Vite dev server and
  by nginx in production); no backend URLs are hardcoded in components.
- **Search/database** — Elasticsearch single node via Docker Compose.
- **Ingestion** — `scripts/` package with a command-line importer
  (`python -m scripts.import_dictionary ...`).

## Requirements

- Docker with the Compose plugin (recommended path)
- Python 3.11+ and Node.js 22+ for running services outside Docker
- Elasticsearch 8.x (provided by Docker Compose)

## Environment configuration

Copy `.env.example` to `.env` and adjust values as needed:

```bash
cp .env.example .env
```

`es_url`, `es_index`, `backend_*`, `cors_origins`, pagination limits,
ingestion batch size, the dictionary source directory, and the log level are
configured here. Application settings flow through `api/config/settings.py`;
`DICTIONARY_SOURCE_DIR` is consumed by Docker Compose as a host bind mount.

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

## Running frontend/backend separately (development)

Backend:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
uvicorn api.main:app --reload
```

Frontend (Vite dev server proxies `/api` to the backend at
`VITE_BACKEND_URL`, default `http://localhost:8000`):

```bash
cd frontend
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

Explicit index mappings are defined by the ingestion pipeline.

## Ingestion

Docker Compose imports the JSON files from `DICTIONARY_SOURCE_DIR` before the
backend starts. A data-and-schema fingerprint stored in the Elasticsearch
mapping skips unchanged data; changed data is validated before the index is
recreated and imported, so invalid input cannot replace the last good index
and removed articles do not linger. `sayings.json` is excluded because it
uses a separate source schema from dictionary articles.

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
cd frontend
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
cd frontend
npm run typecheck
npm run lint
```

## License

MIT — see `license`.
