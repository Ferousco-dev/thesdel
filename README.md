# Thesdel

FastAPI + MongoDB + Redis backend, run locally via Docker Compose. React +
TypeScript frontend lives in [`frontend/`](frontend/) — see
[frontend/README.md](frontend/README.md) and
[frontend/AGENTS.md](frontend/AGENTS.md) for that side.

## Documentation

Start here: [AGENTS.md](AGENTS.md) and [RULES.md](RULES.md) (the engineering
constitution), then [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
[docs/DATABASE.md](docs/DATABASE.md), [docs/SECURITY.md](docs/SECURITY.md),
[docs/API.md](docs/API.md), and the rest of `docs/`.

## Local development

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000 (interactive docs at `/docs` in local env)
- Health: http://localhost:8000/healthz
- Readiness (checks Mongo + Redis): http://localhost:8000/readyz
- MongoDB: localhost:27017
- Redis: localhost:6379

Code under `app/` is bind-mounted into the container with `--reload`, so
edits take effect without a rebuild.

## Running tests

Tests run against in-memory Mongo/Redis fakes (`mongomock-motor`,
`fakeredis`) — no live services required.

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Project layout

See [AGENTS.md](AGENTS.md) for the module map and the rules governing
where new code goes.
