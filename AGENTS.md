# AGENTS.md — Thesdel

Instruction manual for AI coding agents working in this repository. Read
this before touching code. It complements, not replaces, `RULES.md`.

## Project Architecture

Thesdel is a **modular monolith**: one FastAPI application, MongoDB
(primary datastore), Redis (rate limiting, AI usage caps, ephemeral
tokens, job queue backing), ARQ (background jobs), Cloudflare
(DNS/CDN/WAF), R2 (object storage/backups), Resend (email), FCM (push),
React frontend on Vercel.

Full architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Full data model: [docs/DATABASE.md](docs/DATABASE.md).
Full API conventions: [docs/API.md](docs/API.md).
Full security model: [docs/SECURITY.md](docs/SECURITY.md).

## Important Directories

```
app/
├── auth/            # signup, login, session/JWT, password reset, email verify
├── users/           # profile, tier, theme prefs
├── classes/         # class CRUD, membership, join codes
├── timetable/        # timetable_entries CRUD (personal + class)
├── announcements/     # class feed, pinning
├── litheral/
│   ├── study/         # Premium-only — see "Forbidden Patterns" below
│   └── life/            # Pro-only
├── routines/            # Pro-only routine input
├── usage/                # ai_usage_log + Redis cap enforcement
├── progression/           # badges, seasons, thesdel_score, rank
├── streaks/                # partner_streaks
├── billing/                 # webhook handling, tier mutation
├── notifications/            # FCM push
├── files/                     # R2 upload handling
├── audit/                      # security-sensitive action logging
└── shared/                      # db client, config, errors, middleware,
                                  # rate limiter, background job registration
docs/                              # all ADR/architecture/security/etc. docs
```

## Development Commands

(To be filled in once the project skeleton exists — `uv`/`poetry` for
dependency management, `pytest` for tests, `ruff`/`black` for lint/format,
`mypy` for type checking. Do not invent commands that don't exist yet;
check `pyproject.toml` once it's created.)

## Coding Rules

See `RULES.md` for the full constitution. Highlights relevant to day-to-day
work:
- Every protected endpoint re-checks authorization server-side, per
  request, against the database — never trust a client-supplied tier,
  role, or ID as sufficient authorization.
- A module may only call another module's public service function, never
  reach into its repository/model directly. This is what keeps
  `litheral/study` (Premium) structurally unable to touch `routines/`
  (Pro-only) — do not "temporarily" bypass this for convenience.
- Every new database query needs an index behind it, and every new index
  needs a named query pattern justifying it — document both in
  `docs/DATABASE.md` when you add either.
- Every retryable operation (background job, webhook handler, AI
  generation call) must be idempotent — assume at-least-once delivery
  always.

## Security Rules

Full detail in `docs/SECURITY.md`. The two most commonly-violated-by-habit
rules in AI-generated code specifically:
- Never add a "trust the client" shortcut (a role/tier/user-id read from
  the request body instead of resolved server-side) even temporarily to
  get a feature working — this is exactly the class of bug the source
  specs called out by name ("never trust a client-side tier flag").
- Never log PII (timetable content, announcement text, email, name) —
  log IDs and event names only, per `docs/OBSERVABILITY.md`.

## Database Rules

Full detail in `docs/DATABASE.md`. Before adding a collection or field,
check `docs/PRIVACY.md` §1's "why collected" table — every field must map
to a shipped feature, not a speculative future one.

## Testing Rules

Priority order (see `docs/DECISIONS.md` for why this shape): (1)
authorization boundary tests, (2) tier-gating tests, (3) AI-cap
concurrency/race tests, (4) webhook signature/replay tests, (5) core CRUD.
A feature that touches auth, tier-gating, or the AI cap system is not
done until its boundary is tested — this is not optional coverage.

## API Rules

Full detail in `docs/API.md`. New endpoints follow the existing error
envelope, versioning prefix (`/v1/...`), and pagination convention — do not
introduce a one-off pattern for a single endpoint.

## Dependency Rules

Before adding any package: is it necessary, is there an existing
dependency that already does this, what's its maintenance/security
history. Minimize dependency count — this is a small, cost-sensitive
project, not a place to accumulate convenience packages.

## Git Rules

Do not mix feature work with formatting, dependency upgrades, or unrelated
refactoring in one change. Never rewrite history or force-push without
explicit authorization. Only commit when explicitly asked.

## Forbidden Patterns

See `RULES.md` for the full list. Project-specific additions:
- Importing `routines/`'s repository or model from anywhere under
  `litheral/study/` — this is the single most spec-explicit isolation
  requirement in the entire project.
- Reading or mutating `users.tier` / `users.tier_renewed_at` from
  anywhere other than the billing webhook handler.
- Enforcing an AI usage cap by counting `ai_usage_log` rows synchronously
  in the request path without the Redis atomic pre-check — this reopens
  the exact race condition the Redis layer exists to close (see
  `docs/DECISIONS.md` ADR-004).

## Definition of Done

A feature is not complete because the endpoint returns `200`. See
`RULES.md` and the Phase 0 audit's Definition of Done section — at
minimum: authorization enforced, validation present, appropriate indexes
exist, idempotency considered if retryable, tests cover the security
boundary, no PII in logs, relevant `docs/*.md` file updated if the change
affects architecture, data model, security posture, or API surface.

## What Agents Must Inspect Before Changing Code

1. `docs/ARCHITECTURE.md` — which module owns this responsibility.
2. `docs/DATABASE.md` — does the query pattern already have an index; does
   the collection already have the field you're about to add.
3. `docs/SECURITY.md` — does this endpoint/action already have a
   documented threat/mitigation entry.
4. `docs/DECISIONS.md` — has this exact architectural question already
   been decided (don't silently re-decide it differently).
5. `RULES.md` — the constitution; when in doubt, this wins.
