# RULES.md — Engineering Constitution

These rules take precedence over convenience, speed, or "just to get it
working." They apply to every contributor, human or AI. See `AGENTS.md`
for how these rules map to this specific codebase's structure.

## Authentication & Authorization

1. Never bypass authentication, even in a test route, a debug endpoint, or
   "temporarily."
2. Never trust client-supplied authorization — a role, tier, or user-ID
   field in a request body/header is data, not a permission grant. Every
   protected action re-resolves the actor's identity and permissions from
   the server-side session and the database, per request.
3. Never derive `users.tier` from anywhere other than the verified billing
   webhook handler.
4. Never assume an object ID's existence is authorization to access it —
   every resource-scoped query is filtered by a verified ownership/
   membership check.

## Secrets

5. Never store secrets (API keys, DB credentials, JWT signing keys,
   payment provider keys) in source code. Use the environment-variable
   strategy, separated per environment (local/test/staging/production).
   Never commit a `.env` file containing real values.

## Database

6. Never create an unbounded query — every list/read endpoint is paginated
   or explicitly bounded.
7. Never add a database query without considering whether an index serves
   it — and never add an index without a named query pattern that needs
   it. Document both in `docs/DATABASE.md`.
8. Never make a destructive database change (dropping a collection,
   irreversible field removal, bulk deletion) without explicit
   authorization from the user, and never in the same change as unrelated
   feature work.
9. Never let a collection grow an unbounded embedded array — model it as
   a separate, indexed collection instead once growth is unbounded (see
   `docs/DATABASE.md` for the `class_members` precedent).

## Reliability

10. Never add a retry without considering idempotency — assume
    at-least-once delivery for every queue consumer, webhook handler, and
    external API call.
11. Never add a queue consumer without duplicate-delivery protection.
12. Never assume a background job runs exactly once, or that a client
    request is sent exactly once.

## Errors & Observability

13. Never expose internal errors, stack traces, database error messages,
    file paths, or provider-specific details to API clients. Return a
    stable `error_code` and safe `message`; log the detail internally
    against the request's correlation ID.
14. Never log PII (email, name, timetable content, announcement text) in
    application logs — log IDs and event names.
15. Never disable a security control (auth check, rate limit, validation,
    CSP) to make a test pass or unblock a deploy. Fix the underlying
    issue, or explicitly flag the control as wrong to the user — don't
    silently route around it.

## Architecture

16. Never silently change architecture — a decision that affects the
    database, authentication, authorization, billing, or a major
    infrastructure dependency is logged in `docs/DECISIONS.md` and, per
    the project's stop-conditions, confirmed with the user before
    implementation if it's a fundamental change.
17. Never introduce an unnecessary dependency — evaluate maintenance
    status, security history, and whether existing dependencies already
    cover the need, before adding a package.
18. Never create duplicate utilities — search for existing equivalent
    functionality before writing a new helper/service.
19. Never copy-paste business logic across modules — extract a shared
    service function in the owning module and call it, respecting module
    import boundaries (a module calls another module's service interface,
    never its repository/model directly).
20. Never make unrelated changes while fixing a bug — a bug fix touches
    only what the bug requires.

## Testing

21. Never remove or weaken a test to make CI pass — fix the code, or
    determine the test is wrong and get explicit sign-off to change it.
22. Never weaken input validation to accommodate malformed data — reject
    it with a clear validation error instead.

## Code Quality

23. Every file, abstraction, and dependency must have a reason to exist —
    before creating one, confirm equivalent functionality doesn't already
    exist and that the abstraction is actually needed now, not
    speculatively.
24. No placeholder security — an auth check, rate limit, or validation
    rule either exists and works, or the endpoint isn't shipped yet. No
    "TODO: add auth here" in a merged change.
25. No generic names (`data`, `thing`, `manager`, `helper`) where a precise
    name exists.
26. No swallowed errors — a `catch`/`except` block either handles the
    error meaningfully or lets it propagate; it is never empty without a
    documented reason.
