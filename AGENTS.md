Engineering Conventions

General

Prefer production-safe patterns from the start. Do not introduce temporary shortcuts that will need to be removed later.

Use comments and docstrings only when they explain non-obvious constraints, invariants, rationale, or behavior that cannot be made clear through code structure and naming.

Do not write comments or docstrings that merely narrate what the code does.

Avoid magic numbers, magic strings, and scattered configuration.

Keep configuration explicit and centralized.

Hardcoded values are acceptable only when they are true code-level constants. Environment-specific values, credentials, URLs, ports, timeouts, feature settings, and similar configuration belong in the settings layer.

Repository Layout

For a repository/project named <project>, application source must live under a top-level directory with the same name:

<repo-root>/
├── <project>/
│ ├── <service-1>/
│ └── <service-2>/
├── dockerfile.backend
├── dockerfile.frontend
├── .dockerignore
├── .env.example
└── ...

Do not place application service source code directly in the repository root.

Environment Configuration

.env must be gitignored from the start of the project.

Always provide .env.example.

.env.example must mirror the expected .env structure and be usable as a drop-in starting point.

Treat .env as the single source of truth for environment-variable values. Do not duplicate or restate those values in Docker Compose configuration; Compose should consume them from .env (for example, via env_file or variable interpolation as appropriate).

Never commit secrets, credentials, tokens, or environment-specific private values.

In Python applications, use Pydantic Settings for configuration originating from environment variables or .env files.

Application code must consume environment configuration through the settings layer rather than calling os.getenv(), os.environ, or equivalent directly throughout the codebase.

Do not scatter environment-dependent constants throughout implementation code.

Database Schema and Migrations

Use a proper migration tool from the beginning of the project.

For SQLAlchemy applications, use Alembic unless another migration system is intentionally chosen.

Every database schema change must be represented as a migration and committed to the repository.

Treat migration history as the authoritative description of database schema evolution.

Never use Base.metadata.create_all(), metadata.create_all(), or equivalent runtime schema creation as a substitute for migrations.

Do not maintain separate implicit schema initialization logic alongside migrations.

Migrations must be applied before application code depends on the new schema.

Running alembic upgrade head from a container entrypoint is acceptable for development and deployments where only one migration process can run.

For multi-replica or orchestrated production deployments, use a dedicated migration or release step so multiple application instances do not race to perform the same migration.

Docker

Use multi-stage Docker builds.

Dockerfiles must use the lowercase naming convention:

dockerfile.backend
dockerfile.frontend

Follow the same dockerfile.<service> convention for additional services.

Always provide a .dockerignore.

Exclude unnecessary files and directories from the Docker build context, including .git, .env, virtual environments, caches, build artifacts, and node_modules where applicable.

Keep build-time dependencies out of the final runtime image unless required at runtime.

Prefer small and reproducible runtime images.

Pin important base-image and runtime versions deliberately rather than relying on floating defaults.

Never bake secrets or .env files into container images.

Container Security

Runtime containers must not run as root.

Create a dedicated unprivileged user and group in the runtime image and switch to that user with USER.

Copy files with appropriate ownership instead of relying on broad runtime permission changes.

Do not use unnecessarily permissive modes such as chmod 777.

Do not install or depend on sudo in application containers.

Do not enable privileged mode, unnecessary Linux capabilities, host networking, host PID access, or unrestricted host filesystem mounts unless there is an explicit technical requirement.

Keep the final runtime image limited to the packages and executables required to run the service.

Prefer read-only application files at runtime.

Writable directories must be explicit and limited to paths the application actually requires.

Container Entrypoints and Process Startup

Keep deployment concerns and process-runner configuration outside application source code.

Container startup behavior belongs in an entrypoint script, Docker CMD, Compose configuration, an orchestrator, or equivalent deployment configuration.

Entrypoint scripts may perform required startup operations such as migrations before starting the application process.

Entrypoint scripts must use exec when launching the final long-running process so signals are delivered correctly.

Example:

#!/bin/sh
set -eu

alembic upgrade head

exec "$@"

Do not hide deployment behavior inside Python application modules.

Python

Type everything that is meaningfully typeable.

Function parameters must be typed.

Function return values must be typed.

Class and instance attributes must be typed where their type is not already established by a typed declaration.

Collections must use meaningful element types rather than bare list, dict, set, tuple, or similar types.

Avoid Any unless interoperability with an untyped or dynamically typed boundary makes a more precise type impractical.

Do not omit types merely because a human reader could infer them.

New and modified code must pass the project's configured static type checker.

Prefer Pyright or mypy when introducing static type checking to a project that does not already have one.

Keep environment-specific configuration out of implementation logic.

FastAPI

Dependencies

Use Annotated dependencies.

Prefer:

from typing import Annotated

from fastapi import Depends

SomeDependency = Annotated[SomeType, Depends(get_some_dependency)]

For dependencies reused across endpoints, prefer reusable Annotated type aliases instead of repeating Annotated[..., Depends(...)] everywhere.

For example:

DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]

Then use:

async def endpoint(
session: DatabaseSession,
) -> ResponseType:
...

Do not use loosely typed dependency injection when an annotated dependency can express the contract.

Application Lifespan

When the application manages multiple lifespan resources, define a separate async context manager for each resource.

For example:

@asynccontextmanager
async def connection_lifespan(app: FastAPI) -> AsyncIterator[None]:
...

Compose resource lifespans in the application's main lifespan using an AsyncExitStack:

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
async with AsyncExitStack() as stack:
await stack.enter_async_context(connection_lifespan(app))
await stack.enter_async_context(other_resource_lifespan(app))
yield

Do not combine unrelated setup and teardown logic into one monolithic lifespan context manager.

Each resource-specific lifespan must own its corresponding setup and cleanup.

ASGI Server Startup

Application source code must expose the FastAPI application object but must not start the application server itself.

Do not call uvicorn.run() from application code.

Do not embed Uvicorn, Gunicorn, Hypercorn, or another ASGI/WSGI runner into the application lifecycle.

Do not add if **name** == "**main**": blocks whose purpose is to start the deployed application server.

Configure the ASGI server through Docker CMD, an entrypoint, Docker Compose, Kubernetes, systemd, or another deployment mechanism.

For example:

services:
backend:
command: - uvicorn - myproject.backend.main:app - --host - "0.0.0.0" - --port - "8000"

Prefer this separation so application code remains independent of the selected process manager and deployment environment.

Verification Before Completion

Before considering a code change complete:

Run the project's formatter.

Run the project's linter.

Run the configured static type checker.

Run relevant automated tests.

Run migration validation or generation checks when database models or schema-related code changed.

Run container build validation when Dockerfiles, entrypoints, dependency installation, or runtime configuration changed.
