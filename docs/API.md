# API.md — Thesdel

## 1. Conventions

- REST, resource-oriented (`/v1/classes/{id}/timetable`, not RPC-style
  action endpoints, except where an action genuinely isn't a resource
  operation — e.g. `/v1/litheral/study/generate`).
- URL-prefixed versioning from day one: `/v1/...`. Cheap now, expensive to
  retrofit later.
- All request/response bodies validated via Pydantic schemas — server-side
  validation always runs, even though the frontend also validates.
- JSON only. `snake_case` field names (matching the Mongo document shape).

## 2. Authentication

- `Authorization: Bearer <access_jwt>` header on all protected endpoints.
- `POST /v1/auth/refresh` exchanges a valid refresh token (sent via
  `HttpOnly` cookie or request body, per final ADR-002 implementation
  decision) for a new access token, rotating the refresh token.
- Unauthenticated requests to a protected endpoint return `401`, not a
  redirect (this is an API, not a browser app).

## 3. Authorization

- Every endpoint's handler resolves the current user and their tier/role
  from the database per request — never from a client-supplied header or
  cached claim beyond the JWT's own short lifetime.
- Tier-gated endpoints (Litheral, theme customization) use a shared
  `require_tier(min_tier)` dependency that returns `403` with a structured
  `upgrade_required` payload before any downstream cost (especially AI
  cost) is incurred.
- Resource-scoped endpoints (class timetable, announcements) use a shared
  `require_class_membership()` dependency — an object ID existing is never
  sufficient; membership is re-verified per request.

## 4. Error Format

```json
{
  "error_code": "cap_reached",
  "message": "You've used all your regenerations for this period.",
  "request_id": "a1b2c3d4",
  "details": { "resets_at": "2026-09-01T00:00:00Z" }
}
```

- `error_code` is a stable, documented string (not a free-text message) —
  the frontend switches on this, not on `message` text.
- `message` is a safe, user-facing string. Internal exception details,
  stack traces, database errors, and infrastructure specifics are never
  serialized here — they go to structured logs keyed by `request_id`
  instead (see `OBSERVABILITY.md`).
- HTTP status code always matches the error's semantics (`401`
  unauthenticated, `403` forbidden/tier-gated, `404` not found or not
  visible to this user — the two are intentionally indistinguishable for
  IDOR resistance, `409` conflict, `422` validation, `429` rate-limited,
  `503` dependency unavailable).

## 5. Pagination

Cursor-based (not page-number) for feeds that receive concurrent inserts —
announcements feed, badge shelf. Page-number pagination breaks under
concurrent inserts (skipped/duplicated items); cursor pagination doesn't.

```
GET /v1/classes/{id}/announcements?cursor=<opaque>&limit=20
```

## 6. Filtering / Sorting

Supported only where a real query pattern needs it (matching
`DATABASE.md`'s indexed-query-only rule) — e.g. timetable entries filtered
by `day_of_week`, not arbitrary ad-hoc filtering across unindexed fields.

## 7. Rate Limiting

Every rate-limited endpoint returns `429` with a `Retry-After` header when
the limit is hit, and the same structured error envelope (§4) with
`error_code: "rate_limited"`. Limits themselves are documented per-endpoint
in `SECURITY.md` §3, not duplicated here.

## 8. Idempotency

Endpoints where a duplicate client request must not double-execute accept
an `Idempotency-Key` request header:

- `POST /v1/classes/join` (also naturally idempotent via the unique
  `{class_id, user_id}` index — a duplicate join returns the existing
  membership rather than erroring)
- `POST /v1/litheral/study/generate`
- `POST /v1/litheral/study/{block_id}/regenerate`
- `POST /v1/litheral/life/generate`
- `POST /v1/litheral/life/adjust`

A repeated request with the same key within the dedup window returns the
original result rather than re-executing. This is layered on top of, not a
replacement for, the Redis-based AI usage-cap atomicity (ADR-004) — the
idempotency key protects against client-retry duplication; the cap counter
protects against genuinely distinct duplicate taps.

## 9. Deprecation Strategy

A `v1` endpoint marked for removal is announced in this document with a
sunset date before removal, and returns a `Deprecation`/`Sunset` response
header during the transition window. No endpoint is removed without a
prior deprecation period — this is a small app with a mobile client that
can't always force an immediate update.

## 10. Endpoint Map (representative, not exhaustive — grows with
implementation)

```
POST   /v1/auth/register
POST   /v1/auth/login
POST   /v1/auth/refresh
POST   /v1/auth/logout
POST   /v1/auth/verify-email
POST   /v1/auth/request-password-reset
POST   /v1/auth/reset-password

GET    /v1/users/me
PATCH  /v1/users/me

POST   /v1/classes
GET    /v1/classes/preview?join_code=...      (preview before joining — no membership required)
POST   /v1/classes/join                        (body: join_code — user doesn't know class_id yet)
GET    /v1/classes/{class_id}                  (membership required)
GET    /v1/timetable/class/{class_id}          (membership required)
GET    /v1/classes/{class_id}/announcements    (membership required)
POST   /v1/classes/{class_id}/announcements    (rep only)
PATCH  /v1/classes/{class_id}/announcements/{announcement_id}  (rep only — pin/edit)

GET    /v1/timetable                          (personal, current user)
POST   /v1/timetable
PATCH  /v1/timetable/{id}
DELETE /v1/timetable/{id}
POST   /v1/timetable/import                   (image/text upload → parse job)

POST   /v1/litheral/study/generate             (Premium, tier-gated)
POST   /v1/litheral/study/{block_id}/regenerate (Premium, cap-gated)
GET    /v1/litheral/study

POST   /v1/litheral/routines                   (Pro, tier-gated)
POST   /v1/litheral/life/generate               (Pro, tier-gated)
POST   /v1/litheral/life/adjust                  (Pro, cap-gated)
GET    /v1/litheral/life

GET    /v1/usage/ai                              (remaining caps this period)

GET    /v1/profile/{user_id}                      (public progression view)
GET    /v1/badges
GET    /v1/streaks/{user_id}
POST   /v1/streaks/invite
POST   /v1/streaks/{id}/accept

PATCH  /v1/users/me/theme                          (Pro-gated for custom accent)

POST   /v1/billing/webhook                          (provider-specific, signature-verified)
```
