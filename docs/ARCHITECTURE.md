# ARCHITECTURE.md — Thesdel

## 1. System Overview

Thesdel is a modular monolith: a single FastAPI application, MongoDB as the
primary datastore, Redis for rate limiting/caps/ephemeral state, background
jobs via ARQ (Redis-backed), Cloudflare as DNS/CDN/WAF in front of the app,
R2 for object storage and backups, Resend for transactional email, FCM for
push notifications, and a React frontend on Vercel.

```
                         ┌─────────────┐
                         │  Cloudflare │  DNS / CDN / WAF
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
   React (Vercel) ─────► │  FastAPI    │ ◄──── FCM (push out)
                         │  monolith   │
                         └──┬───────┬──┘
                            │       │
                     ┌──────▼─┐   ┌─▼──────┐
                     │ MongoDB│   │  Redis │
                     └────────┘   └───┬────┘
                                       │
                                ┌──────▼──────┐
                                │ ARQ workers │──► Resend (email)
                                │ (background)│──► LLM API (Litheral)
                                └─────────────┘──► R2 (uploads/backups)
```

## 2. Module Boundaries

```
app/
├── auth/            # signup, login, session/JWT, password reset, email verify
├── users/            # profile, tier, theme prefs
├── classes/          # class CRUD, membership, join codes
├── timetable/         # timetable_entries CRUD (personal + class)
├── announcements/     # class feed, pinning
├── litheral/
│   ├── study/         # Premium-only: reads timetable + study_plans ONLY
│   └── life/           # Pro-only: reads timetable + study_plans + routines
├── routines/           # Pro-only routine input
├── usage/               # ai_usage_log + Redis cap enforcement
├── progression/          # badges, seasons, thesdel_score, rank
├── streaks/               # partner_streaks
├── billing/                # webhook handling, tier mutation, verified-badge
├── notifications/            # FCM push
├── files/                     # R2 upload handling (timetable import images)
├── audit/                      # security-sensitive action logging
└── shared/                      # db client, config, error types, middleware,
                                  # rate limiter, background job registration
```

**Import rule (enforced by code review, not tooling, at current scale):**
a module may only depend on another module's public service interface, never
on its repository or ORM model directly. This is what makes the Premium/Pro
data isolation requirement structural rather than a convention someone can
forget: `litheral/study` has no import path to `routines/`'s repository at
all — attempting the import is a visible code-review-time violation, not a
runtime check.

## 3. Request Lifecycle

1. Request hits Cloudflare (WAF/DDoS filtering, TLS termination) → FastAPI.
2. Middleware chain: request-ID assignment → structured logging context →
   rate limiter (Redis) → auth (JWT verification, resolves current user +
   tier from Mongo, never from a client-supplied field) → route handler.
3. Route handler validates input via Pydantic schema → calls the owning
   module's service function → service enforces authorization (ownership,
   tier, membership) → repository layer executes the Mongo query/write.
4. Response serialized through a consistent envelope (see `API.md`).
5. Side effects requiring more than a few hundred ms (AI generation, email,
   push) are enqueued to ARQ, not executed inline.

## 4. Authentication Flow

See `DECISIONS.md` ADR-002 (pending sign-off) and `SECURITY.md` for full
detail. Summary: Argon2id password hashing → short-lived (~15 min) JWT
access token → server-side refresh token (hashed at rest, rotated on use,
reuse-detected) in a `sessions` collection, allowing per-device
revocation and logout-everywhere.

## 5. Authorization Flow

Every protected endpoint re-resolves the current user's tier and
resource ownership from MongoDB on every request — never trusts a
client-supplied tier flag or a cached claim beyond the short JWT lifetime.
Class-scoped resources (timetable entries, announcements) are filtered by a
verified `class_members` lookup, not by object-ID match alone — an ID
existing is not authorization to access it (mitigates IDOR/BOLA, see
`SECURITY.md`).

Tier-gating pattern: a FastAPI dependency (`require_tier(min_tier)`)
resolves the user's current tier from the DB and raises `403` with a
structured `upgrade_required` payload before any AI cost is incurred,
matching the Backend Spec's explicit requirement.

## 6. Database Architecture

See `DATABASE.md` for the full collection-by-collection design. Summary:
MongoDB Atlas (replica-set-backed even on free/shared tier, enabling
multi-document transactions where genuinely needed — see `DATABASE.md`
§Concurrency). No relational joins; access patterns are pre-modeled per
collection with compound indexes.

## 7. Redis Architecture

Redis is used for:
- Rate limiting (sliding window / token bucket per endpoint class)
- AI usage-cap atomic counters (`INCR`/`EXPIRE`, keyed
  `user_id:feature:billing_period`)
- Short-lived tokens (email verification, password reset)
- ARQ job queue backing store

**Redis is never the source of truth for permanent business data.** TTLs:
cap counters expire at the billing-period boundary; verification/reset
tokens expire in 15–60 minutes; rate-limit windows expire per their window
size (seconds to minutes).

**Failure behavior if Redis is unavailable:**
- Auth-endpoint rate limiting: fail closed (reject with 503) — brute-force
  protection is not optional.
- AI-cap enforcement: fail closed (reject the AI call) — this is the
  product's primary cost-control mechanism per the Backend Spec's own
  priority ordering; failing open would remove it entirely.
- General read-endpoint rate limiting: fail open with a conservative
  in-process fallback limiter, so a Redis outage doesn't take down basic
  timetable viewing.
- ARQ job enqueue: jobs queue in-memory briefly and retry enqueue; if Redis
  stays down, user-facing actions that depend on a background job (e.g.
  "email sent") surface a clear "processing delayed" state rather than a
  silent failure.

## 8. Queue / Background Job Architecture

ARQ (Redis-backed, asyncio-native) runs jobs for: AI generation calls
(Litheral study/life generation — see below), transactional email (Resend),
push notifications (FCM), and scheduled cleanup (e.g. expired
verification tokens).

All workers assume **at-least-once delivery** — no job assumes it runs
exactly once. Idempotency is designed at the job level (see `RULES.md`
"never add a retry without considering idempotency"): AI generation jobs are
keyed by a request idempotency key so a retried job doesn't double-generate
or double-charge the usage cap; email jobs check a `sent_at` marker before
sending; notification jobs are naturally idempotent-safe to over-send but
are still deduplicated to avoid spamming users.

Retry policy: exponential backoff, max 5 attempts, then dead-letter (logged,
not silently dropped) with alerting.

## 9. External Services

- **MongoDB Atlas** — primary datastore.
- **Redis (Upstash or equivalent)** — caps, rate limiting, queue backing.
- **Cloudflare** — DNS, CDN, WAF only (not compute — no Workers/KV/Queues
  used; see `DECISIONS.md` and `RESEARCH.md` #7 for why).
- **Cloudflare R2** — object storage for uploaded timetable-import images
  and periodic DB backup exports.
- **Resend** — transactional email (verification, password reset, security
  notifications).
- **FCM** — push notifications (class announcements, study-block reminders).
- **LLM API (provider TBD, see `RESEARCH.md` #2 and `DECISIONS.md` ADR-007
  equivalent open item)** — used only for natural-language timetable-import
  parsing, never for core time-slotting math (see ADR-003).
- **Payment provider(s), market-specific** — TBD, see ADR-007.
- **Vercel** — React frontend hosting.

## 10. File Storage

Uploaded timetable-import images: validated (MIME allow-list, size cap),
re-encoded server-side (strips embedded scripts/metadata, defends against
disguised file types and image-bomb dimensions) before being written to R2.
Never served directly from user-controlled paths; access is via
short-lived signed URLs scoped to the owning user.

## 11. Notification Architecture

FCM push for: class announcements (new post, especially pinned), study-block
reminders (Premium/Pro), and Pro life-schedule conflict alerts. Enqueued via
ARQ, not sent inline from the request path. Notification content generation
never triggers an AI usage-cap deduction — pushes are template-based, not
LLM-generated.

## 12. Backup Architecture

See `DISASTER_RECOVERY.md` for full detail. Summary: MongoDB Atlas automated
snapshots (managed) plus a periodic independent export to R2, keeping a
second copy outside the primary provider's control plane.

## 13. Failure Handling — Summary

Full failure-first analysis lives per-feature in code review, but the
system-wide defaults are:
- **Database unavailable:** requests fail with a 503 and a stable error
  code; no silent partial responses.
- **Redis unavailable:** see §7 above — failure direction differs by
  criticality (fail closed for security-critical paths, fail open with a
  conservative fallback for read paths).
- **LLM API timeout/unavailable:** AI generation job retries with backoff;
  if it ultimately fails, no usage-cap deduction is charged for the failed
  attempt's *outcome*, but the *attempt* is still logged to `ai_usage_log`
  per the Backend Spec's explicit instruction ("log attempts, not just
  completions, so retries are still capped") — the cap counter increments
  on attempt, and a failed attempt does not refund it, preventing a
  cap-bypass-via-induced-failure abuse vector.
- **Webhook delivery failure/retry:** idempotent by event ID; safe to
  receive the same webhook multiple times.
