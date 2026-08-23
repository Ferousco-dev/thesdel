# SECURITY.md — Thesdel

## 1. Threat Model

| Asset | Threat | Mitigation |
|---|---|---|
| AI compute budget | Cap-bypass via concurrent duplicate requests (race) | Redis atomic `INCR`/`EXPIRE` pre-check before any LLM call, not a post-hoc log count (ADR-004) |
| `users.tier` | Client sets tier directly; forged/replayed webhook | Tier mutated only inside the billing webhook handler after signature verification + event-ID idempotency; every gated endpoint re-resolves tier server-side per request from the DB, never from a client-supplied field or a stale JWT claim |
| Class-scoped data | IDOR/BOLA — user A reads/edits class B's timetable/announcements by guessing an ID | Every class-scoped query filtered by a verified `class_members` lookup, not ID match alone |
| `routines` (Pro) data | Premium user or a future bug exposes Pro-only data | Module-level isolation: `litheral/study` has no import path to the routines repository (structural, not a query filter that could be forgotten) — see `ARCHITECTURE.md` §2 |
| Auth endpoints | Credential stuffing / brute force | Redis-backed sliding-window limiter, per-IP and per-account; generic error messages (no "email not found" enumeration); fails closed if Redis is down |
| Password reset / email verification | Token guessing, reuse, or flooding a target's inbox | Cryptographically random tokens, short TTL (15–60 min), single-use, rate-limited per account and per IP |
| Payment webhook | Replay or forged webhook grants free tier upgrade | Signature verification (provider-specific HMAC) + idempotency on the provider's event ID to reject replays |
| File upload (timetable import) | Malicious/oversized file, disguised type, image bomb | MIME allow-list, size cap, server-side re-encode before storage, never trust client `Content-Type` header |
| Announcements | Compromised rep account posts spam/abuse to a whole class | Per-rep rate limit on posts; audit-logged post/pin/delete actions |
| Partner streaks | Enumeration to spam-create streaks with arbitrary users | Mutual opt-in required (invite/accept flow), not open creation by supplying another user's ID |
| Session/refresh tokens | Stolen refresh token used after legitimate rotation | Refresh-token rotation on every use; reuse of an already-rotated token triggers full session-family revocation (theft signal) |

## 2. Authentication

- Password hashing: **Argon2id** (OWASP current recommendation — see
  `RESEARCH.md` #5). Never a reversible or fast-hash scheme.
- Access token: short-lived JWT (~15 min), signed with a server-held secret
  (never exposed to the client, rotated via the environment-variable
  strategy in §7).
- Refresh token: opaque, random, hashed at rest in the `sessions`
  collection, rotated on every use, reuse-detected (see ADR-002).
- Email verification required before certain actions (e.g. class creation
  as a rep) — exact gating TBD at implementation time, but signup itself is
  never blocked on verification (avoids friction on a mobile-first product).
- Login/registration/password-reset endpoints are rate-limited distinctly
  from general API traffic (see §3).
- Generic, non-enumerating error messages on login and password-reset
  (never reveal whether an email exists).

## 3. Rate Limiting

Per-operation, Redis-backed (sliding window), not a single global limit:

| Operation | Limit basis | Notes |
|---|---|---|
| Login | Per-IP + per-account | Tight; fails closed if Redis down |
| Registration | Per-IP | Prevents mass fake-account creation |
| Password reset request | Per-account + per-IP | Prevents inbox-flooding and enumeration probing |
| Email verification resend | Per-account | |
| AI generation (study/life) | Per-account, per billing period | This is the usage-cap system itself (ADR-004), not a burst limiter |
| General authenticated reads | Per-account, generous | Fails open with a conservative in-process fallback if Redis is down (see `ARCHITECTURE.md` §7) |
| Class join | Per-account | Prevents join-code brute-forcing |
| Announcement posting | Per-rep-account | Abuse containment |
| Webhook endpoint | Per-source-IP allowlist + signature | Not a general rate limit — trust is established by signature, not volume |

Every important limit is config-driven, not hardcoded, per the Backend
Spec's own guidance on AI caps — the same principle applies to rate limits
generally, since they'll need tuning after real traffic data exists.

## 4. Authorization (RBAC)

Roles are coarse and resource-scoped, not a global RBAC matrix:
- **Platform tier** (`free` | `premium` | `pro`) — gates feature access
  (Litheral, theming), resolved server-side per request.
- **Class role** (`rep` | `member`) — scoped per class in `class_members`,
  gates announcement posting/pinning and class-settings edits.
- No platform-admin role exists in the current spec. A moderation/admin
  surface is a missing requirement (see Phase 0 audit §5) — flagged for
  product decision, not silently added.

Authorization is never inferred from the frontend. Every protected
mutation re-checks ownership/role/tier server-side, per request, against
the database — matching the Backend Spec's explicit "never trust a
client-side tier flag" instruction, generalized to all authorization
checks.

## 5. Input Validation

All external input — request body, query params, path params, headers,
uploaded files, webhook payloads, third-party API responses (the LLM's
output) — validated via Pydantic schemas at the FastAPI boundary. LLM
output specifically is treated as untrusted structured data: validated
against an expected schema before being written to `study_plans` /
`life_schedule_blocks`, never executed or interpolated into a query
unvalidated.

## 6. File Upload Security

- MIME allow-list (image types only for timetable import).
- Size cap enforced before the full body is read into memory.
- Server-side re-encode (strip metadata, normalize format, bound
  dimensions) before persisting to R2 — defends against disguised file
  types and decompression/image-bomb attacks.
- Never trust the client-supplied `Content-Type` header for validation
  decisions; sniff actual content.
- Stored objects are never served from a guessable/public path — access via
  short-lived signed URLs scoped to the owning user.

## 7. Secrets

- No secret (DB credentials, JWT signing key, LLM API key, Resend key,
  payment provider keys, R2 credentials) is ever committed to source
  control.
- Environment-variable strategy separates local / test / staging /
  production, each with its own secret values — no shared secrets across
  environments.
- `.env` files with real values are gitignored; only `.env.example` with
  placeholder keys is committed.

## 8. Security Headers / Transport

- TLS enforced end-to-end (Cloudflare terminates at the edge; origin
  connection also encrypted).
- HSTS enabled.
- CSP configured for the API responses (JSON API — restrictive by default;
  the frontend's own CSP is a separate concern documented alongside the
  frontend build).
- CORS restricted to the known frontend origin(s) (Vercel deployment URL +
  custom domain), not a wildcard.
- Cookies (if used for any session component) marked `HttpOnly`, `Secure`,
  `SameSite=Strict` or `Lax` as appropriate.

## 9. Webhook Security

Applies to the payment provider webhook (and any future webhook source):
- Signature verified using the provider's documented HMAC scheme before
  any payload field is trusted.
- Payload validated against an expected schema.
- Idempotency: the provider's event ID is stored and checked — a replayed
  or duplicate-delivered webhook is a no-op on the second delivery, not a
  double-processed tier change.
- Processing is queued (ARQ) so a slow downstream step doesn't cause the
  webhook endpoint to time out and trigger a provider retry storm.
- Correct HTTP status returned so the provider's own retry logic behaves as
  it expects (2xx only on confirmed processing).

## 10. Audit Logging

Security-sensitive actions logged with actor identity, timestamp, and
request-correlation ID, sensitive-data-free:

- Login, logout, failed login attempts
- Password change, email change
- Tier change (via webhook only — logged with the triggering event ID)
- Class role changes (member → rep)
- Announcement post/pin/delete (rep actions)
- Account deletion

Audit logs are structured (JSON), timestamped, and stored separately from
general application logs so they aren't rotated/dropped on the same
retention schedule as debug-level noise.

## 11. Incident Response

- Any suspected credential/secret compromise: rotate the affected secret
  immediately via the environment-variable strategy (§7), revoke all active
  sessions if user credentials are implicated.
- Suspected mass-abuse of AI caps or rate limits: caps and limits are
  config-driven specifically so they can be tightened without a code
  deploy during an active incident.
- Suspected data breach: full incident response procedure (containment,
  assessment, notification obligations per market) is a product/legal
  decision to formalize — not yet defined; flagged as a gap to close before
  production launch, not before this document is written.
