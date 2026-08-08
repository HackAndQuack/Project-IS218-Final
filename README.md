# Calculations App

A FastAPI web application with JWT-based authentication and full BREAD (Browse, Read, Edit, Add,
Delete) support for calculations. Users register, log in, and manage a personal history of
addition, subtraction, multiplication, and division calculations through both a REST API and a
server-rendered web UI.

- **API**: `POST /calculations`, `GET /calculations`, `GET /calculations/{id}`,
  `PUT /calculations/{id}`, `DELETE /calculations/{id}` — all scoped to the authenticated user.
  `GET /users/me` and `PUT /users/me` for profile info, `PUT /users/me/password` for password
  changes. Interactive docs at `/docs` (Swagger UI) and `/redoc`.
- **Web UI**: `/`, `/login`, `/register`, `/dashboard` (browse + add), `/dashboard/view/{id}`
  (read), `/dashboard/edit/{id}` (edit), with delete available from both the dashboard and the
  view page. `/profile` for updating account info and changing your password.

## Running the app

### With Docker (recommended)

```bash
docker-compose up --build
```

This starts the FastAPI app on [http://localhost:8000](http://localhost:8000), a PostgreSQL 17
database, and pgAdmin at [http://localhost:5050](http://localhost:5050)
(`admin@example.com` / `admin`). Tables are created automatically on startup.

### Without Docker

1. Have a PostgreSQL instance available and export a `DATABASE_URL` (or create a `.env` file —
   see `app/core/config.py` for all supported settings):

   ```bash
   export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fastapi_db
   export JWT_SECRET_KEY=change-me-to-something-random-32-chars-plus
   export JWT_REFRESH_SECRET_KEY=change-me-too-something-random-32-chars
   ```

2. Install dependencies and run the app:

   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

3. Visit [http://localhost:8000](http://localhost:8000).

## Running tests locally

The test suite has three layers: unit tests (`tests/unit`), API integration tests
(`tests/integration`), and browser-driven Playwright E2E tests (`tests/e2e`). The E2E and
integration tests boot a real `uvicorn` server against your `DATABASE_URL`, so a reachable
PostgreSQL instance is required (e.g. `docker-compose up db`).

```bash
pip install -r requirements.txt
playwright install --with-deps chromium

# Run everything (unit + integration + e2e)
pytest

# Skip the slower, browser-driven E2E tests
pytest -m "not e2e"

# Only the BREAD end-to-end UI tests
pytest tests/e2e/test_calculation_bread_e2e.py -v
```

Coverage reports are generated automatically per `pytest.ini` (terminal + `htmlcov/`).

## Database migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/) (`alembic.ini`,
`migrations/`). `migrations/env.py` reads the target schema from `app.database.Base.metadata` and
the connection string from `settings.DATABASE_URL`, so no separate configuration is needed beyond
what's already in `app/core/config.py`.

```bash
# Apply all pending migrations (creates tables on a fresh database)
alembic upgrade head

# After changing a SQLAlchemy model, generate a migration for the diff
alembic revision --autogenerate -m "describe the change"

# Roll back the most recent migration
alembic downgrade -1
```

Note: the app's `lifespan` startup hook and the test suite (`tests/conftest.py`) still use
`Base.metadata.create_all`/`drop_all` directly for convenience — Alembic is the source of truth for
real deployments, but tests intentionally keep their own fast, disposable schema setup.

## CI/CD

`.github/workflows/test.yml` runs on every push/PR to `main`, as three sequential jobs:

1. **test** — installs dependencies, installs Playwright's Chromium browser, spins up a
   PostgreSQL service container, and runs the full `pytest` suite (unit + integration + e2e).
2. **security** — builds the Docker image and scans it with
   [Trivy](https://github.com/aquasecurity/trivy) for HIGH/CRITICAL vulnerabilities
   (`.trivyignore` documents the two findings that are false positives from pip's own vendored
   dependencies, not this project's code).
3. **deploy** — on pushes to `main` only, once `security` passes, builds and pushes the image to
   Docker Hub via Buildx, tagged `latest` and with the commit SHA.

The deploy job requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` to be configured as repository
secrets (Settings → Secrets and variables → Actions).

Docker Hub repository: <https://hub.docker.com/r/hackandquack/project-is218-module-14>

## Project layout

- `app/main.py` — FastAPI app: web routes, auth endpoints, and the calculations BREAD endpoints.
- `app/models/calculation.py` — polymorphic SQLAlchemy models (Addition/Subtraction/
  Multiplication/Division) with a factory method and per-type `get_result()`.
- `app/schemas/calculation.py` — Pydantic request/response schemas and validation rules.
- `templates/` + `static/` — Jinja2 templates and CSS/JS for the web UI.
- `tests/unit`, `tests/integration`, `tests/e2e` — the three test layers described above.
- `docs/` — module-by-module walkthroughs of how this project was built (course reference
  material).

## Further reading

See `docs/00-course-overview.md` through `docs/08-containerization.md` for a guided walkthrough of
how each part of this application (models, schemas, auth, API endpoints, frontend, testing, and
containerization) was built.

## Reflection

For the final feature, I picked user profile & password change over the other options, mainly
because `app/schemas/user.py` already had fully validated `UserUpdate` and `PasswordUpdate`
schemas sitting unused in the codebase.

I split the work into three branches (CI/CD fix, Alembic, then the feature), merging each before
starting the next.

A few surprises along the way:

- Swapping in the "correct" auth dependency (a real DB-backed user lookup instead of one that
  faked a user object from the JWT) immediately broke the app, because it activated a dormant
  Redis-backed token blacklist check — and there's no Redis anywhere in this project. The two bugs
  had been silently canceling each other out. I made that check fail open when Redis is
  unreachable, consistent with the "optional" label already on that config setting.
- Fixing the security scan meant bumping a few vulnerable dependencies, which pulled in a major
  Starlette upgrade that changed how `TemplateResponse` is called.
- Not every scanner finding is real: two Trivy results traced back to files vendored inside pip's
  own internals, not anything the app actually uses. I verified that by hand before documenting the
  exclusions in `.trivyignore`.
