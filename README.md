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

## Frontend development

The frontend is a React + TypeScript application built with Vite. Its source
lives in [`frontend/src/`](frontend/src/), with routing, authentication, API
access, and shared design tokens separated into their respective modules.

```bash
cd frontend
npm install
npm run dev
```

Available frontend checks:

```bash
npm run build       # Type-check and create a production build
npm run typecheck   # Type-check without emitting a build
npm run lint        # Run ESLint with warnings treated as errors
npm run test        # Run the Vitest suite
```

### Frontend architecture

- `src/routes/` contains page-level routes such as login, timetable, classes,
  Litheral, and profile.
- `src/components/` contains shared UI such as tier gates and bottom
  navigation.
- `src/lib/api/` is the only frontend boundary for backend endpoint calls;
  components should use functions from `endpoints.ts` rather than calling
  `fetch` directly.
- `src/lib/auth/` owns authentication state and token lifecycle behavior.
- `src/styles/theme.css` contains shared design tokens, accessibility sizing,
  light/dark theme values, and button primitives.

The marketing/landing page (`src/routes/LandingPage.tsx`, plus the standalone
About/Contact/Support/Privacy/Terms/Cookies pages under
`src/routes/marketing/`) is a real React route at `/`, not a standalone HTML
file — `frontend/index.html` is the normal Vite entry point (`#root` +
`/src/main.tsx`). It uses Tailwind (loaded via CDN in `index.html`, scoped to
these marketing pages only) and Plus Jakarta Sans alongside the rest of the
app's own design tokens, since it was ported from an externally supplied
design rather than built from `theme.css` like the authenticated app screens.

## Project layout

See [AGENTS.md](AGENTS.md) for the module map and the rules governing
where new code goes.
