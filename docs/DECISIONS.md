# DECISIONS.md — Architecture Decision Record

Each entry: Decision, Context, Alternatives, Reason, Consequences. Numbered
sequentially, never renumbered or deleted — superseded decisions are marked
superseded, not removed.

---

## ADR-001: Replace Supabase (Postgres + Auth) with MongoDB + FastAPI-native auth

**Status:** Accepted (stack direction set by product owner)

**Context:** The original Backend Spec suggested Supabase as a
cost-near-zero managed backend. Product direction has since moved to
MongoDB, Redis, Cloudflare, Resend, Vercel, R2, FCM, with FastAPI as the
application framework.

**Alternatives considered:**
- Keep Supabase (Postgres + Auth) — rejected, superseded by explicit product
  direction.
- MongoDB with a third-party auth service (Auth0, Clerk) — rejected for now;
  adds a paid dependency and external attack surface not justified at this
  scale, though revisitable if in-house auth proves too costly to maintain.

**Reason:** Explicit product direction; MongoDB's document model fits the
mostly-independent, denormalization-tolerant collections in this domain
(timetables, announcements, badges) better than forcing a relational shape.

**Consequences:** Auth, session management, and all CRUD authorization logic
must be built in-house (see ADR-002). Relational integrity (foreign keys,
composite-key uniqueness) becomes an application/index responsibility
instead of a database guarantee — mitigated via compound unique indexes
(see `DATABASE.md`).

---

## ADR-002: Auth architecture — JWT access token + server-side refresh token

**Status:** Accepted (confirmed by user 2026-08-23)

**Context:** Supabase Auth previously handled password hashing, session
tokens, verification, and reset invisibly. That's gone. A first-class
decision is needed.

**Alternatives considered:**
- Pure server-side session cookies (session ID in an HttpOnly cookie, full
  session state in Mongo/Redis) — simpler revocation model, but less natural
  for a mobile-first client (frontend spec is explicitly mobile-first)
  hitting a REST API, where bearer tokens are the more common pattern.
- Bare stateless JWT with no refresh mechanism — rejected: cannot revoke
  before expiry, breaks "logout everywhere" and forced re-auth after
  password change.

**Reason:** Short-lived access JWT (~15 min) + longer-lived, server-side,
revocable, rotated-on-use opaque refresh token balances mobile-client
ergonomics with real revocation, per OWASP JWT and Session Management
guidance (see `RESEARCH.md` #6).

**Consequences:** Requires a `sessions` collection (refresh token hash,
device metadata, expiry) and refresh-rotation logic with reuse detection.
Adds implementation surface Supabase previously hid — sized as its own
roadmap phase.

**Follow-up:** Awaiting explicit confirmation before implementation begins.

---

## ADR-003: No vector search / no ML-based scheduling in V1

**Status:** Accepted

**Context:** Backend Spec §5.2 explicitly recommends a rules-based
constraint solver over an ML/LLM-driven planner for V1, using an LLM only
for natural-language timetable-import parsing.

**Alternatives considered:**
- MongoDB Atlas Vector Search for "smart" schedule suggestions — rejected,
  no current requirement, would be speculative infrastructure.
- Full ML personalization model for Pro's "learns your routine" claim —
  rejected per the spec's own guidance; V1 uses heuristics (weighting
  previously-confirmed time slots) instead.

**Reason:** Matches both the source spec's stated preference and the master
prompt's anti-overengineering rule.

**Consequences:** Litheral V1 = constraint/bin-packing solver + a scoped LLM
call only for import parsing. Revisit if a genuine semantic-search feature
is scoped later.

---

## ADR-004: Redis as the AI-usage-cap and rate-limit enforcement point

**Status:** Accepted

**Context:** AI compute is described as "the single most important
cost-control mechanism in the whole backend." Concurrent duplicate requests
create a check-then-log race if enforcement is Mongo-only.

**Alternatives considered:**
- Mongo multi-document transaction on `ai_usage_log` for check-then-write —
  works, but couples the general rate-limiting need (auth endpoints, etc.)
  to Mongo instead of reusing one mechanism for both.

**Reason:** Redis `INCR`/`EXPIRE` gives an atomic, single-round-trip cap
check reusable as the same primitive for endpoint rate limiting generally
(see `RESEARCH.md` #4).

**Consequences:** Redis becomes a dependency in the critical path of every
AI-backed request and every auth request. Failure-mode behavior is
therefore specified explicitly (see `ARCHITECTURE.md` — Redis Unavailability)
rather than left implicit.

---

## ADR-005: No microservices; modular monolith on FastAPI

**Status:** Accepted

**Context:** Master prompt requires a monolith with internal module
boundaries strong enough to theoretically extract later, without actually
building fake microservices.

**Reason:** Team size, current scale, and the master prompt's explicit
instruction.

**Consequences:** Module boundaries (see `ARCHITECTURE.md`) are enforced by
import discipline and code review, not network boundaries. The
Premium/Pro data-isolation requirement (Premium code path must never touch
`routines`) is enforced the same way — by construction, via which modules
are allowed to import which repositories.

---

## ADR-006: Account deletion / permanent-badge tension

**Status:** Accepted (confirmed by user 2026-08-23)

**Context:** Backend Spec describes `thesdel_score` as "permanent,
always-increasing" and `user_badges` as "permanent, never deleted." This
conflicts with a standard account-deletion / right-to-erasure requirement.

**Alternatives considered:**
- Hard-delete everything on account deletion, including score/badges —
  rejected, breaks the spec's "permanent, never deleted" badge/score intent
  and destroys leaderboard/season integrity.
- Defer deletion entirely until a specific market's legal requirement
  forces the decision — rejected, this ADR now resolves it.

**Reason:** "Account deletion" is redefined as deactivation, not row
deletion. A user-initiated deletion request:
1. Sets the account record's `status` to `inactive` (the `users` document
   itself is never hard-deleted).
2. Strips/anonymizes PII on that record (email, name, and any other
   directly-identifying fields) per `docs/PRIVACY.md`.
3. Leaves `thesdel_score`, `user_badges`, season/rank history untouched and
   still attributed to the (now-anonymized) account ID — this satisfies
   both "permanent, always-increasing" and leaderboard/season integrity,
   since the ID persists even though the identity behind it no longer
   resolves to PII.
4. Invalidates all sessions/refresh tokens for the account immediately.

**Consequences:**
- Every module that reads `users.status` for access control must treat
  `inactive` as "cannot authenticate, cannot use the product" — this is an
  auth-layer gate, not a progression-layer concern.
- No module ever hard-deletes a `users` document; there is no
  account-deletion code path that removes the row.
- `progression` (badges, `thesdel_score`, seasons, rank) can be built
  against the assumption that a `user_id` referenced by a badge/score
  record is permanent and never disappears — no orphan-handling logic is
  needed for that dimension.
- The actual deactivation endpoint/flow (in `auth` or `users`) is a
  separate piece of work from `progression` itself and is not implemented
  as part of this ADR — this ADR only fixes the data-retention policy so
  `progression` is unblocked.

---

## ADR-007: Payment provider — deferred, provider-agnostic webhook interface

**Status:** Open — blocking Roadmap Phase 6 (Billing) only.

**Context:** NG/PK/LK have different dominant payment rails; no single
global provider assumption is safe.

**Reason:** Explicitly flagged as unresolved in the original Backend Spec.

**Consequences:** `billing` module built against a provider-agnostic
interface (signature verification + event-ID idempotency) so a specific
provider can be plugged in per market later without touching tier-mutation
logic.

---

## ADR-008: Rank heuristic — absolute thesdel_score thresholds (first pass)

**Status:** Accepted, first-pass — open follow-up noted below.

**Context:** `users.rank` is in the schema and the Backend Spec references
a rank concept tied to `thesdel_score` and seasons, but no exact tier
names/thresholds or season-relative formula (e.g. percentile-within-season
leaderboard rank) are documented anywhere available to this module.
Building a full leaderboard/percentile ranking system without a spec would
be over-engineering a first pass of `app/progression/`.

**Decision:** `compute_rank()` in `app/progression/service.py` derives rank
from absolute, always-increasing `thesdel_score` via fixed thresholds
(Unranked / Rising / Contender / Elite / Legend), independent of season.
Recomputed and persisted to `users.rank` whenever `add_score()` runs.

**Consequences:**
- Rank is simple, deterministic, and season-agnostic for now — it does not
  reset at a season boundary, and it does not reflect a user's standing
  relative to other users this season.
- **Open follow-up (not built here):** a season-relative/leaderboard rank
  (e.g. percentile within the current `seasons` window) if the product
  actually wants seasonal competition semantics — this is a product/spec
  question, not an engineering blocker, and should be resolved before
  building it rather than guessed at again.

---

## ADR-009: Partner streaks — interaction trigger and stale-reset window (first pass)

**Status:** Accepted, first-pass — open follow-up noted below.

**Context:** `docs/DATABASE.md`'s `partner_streaks` sketch and
`docs/SECURITY.md`'s threat table establish the shape (`current_streak`,
`last_interaction_at`, `status`, mutual opt-in via invite/accept) but do not
specify (a) what user action counts as an "interaction" that increments
`current_streak`, or (b) how long a pair can go without interacting before
the streak is considered broken. Building a large interaction-detection
surface (e.g. deriving "interaction" from cross-module activity such as
shared study sessions) without a spec would be over-engineering a first pass
of `app/streaks/`.

**Decision:**
1. **Interaction = an explicit daily check-in.** `POST
   /v1/streaks/check-in` is callable by either member of an *active* pair
   and increments `current_streak` at most once per UTC calendar day for
   that pair (a same-day repeat call is an idempotent no-op, not an error).
   This is the smallest reasonable V1 surface — a dedicated event, not an
   inference from other modules' data, which would create an unreviewed
   cross-module coupling.
2. **Stale-reset window = 48 hours** since `last_interaction_at`. Checked
   lazily on the next read or check-in (`app/streaks/service.py`'s
   `_apply_lazy_reset` / the staleness check inside `check_in`) rather than
   via a scheduled job — RULES.md #23 and the project's stated preference
   for simplicity over speculative infra. 48h (not a strict 24h) tolerates
   a user checking in once "per day" without being penalized by timezone
   drift or checking in slightly later than exactly 24h from the last time.

**Alternatives considered:**
- Inferring "interaction" from existing activity (e.g. both partners having
  a completed study session that day) — rejected: couples `streaks` to
  other modules' internals or requires a new shared event bus that doesn't
  exist yet; a large feature surface for a first pass.
- Cron-based nightly reset job — rejected: adds a background job and its
  own idempotency/retry surface for something a lazy check on access
  achieves identically, per RULES.md #23.
- Exact 24h stale window — rejected: too easy to break a streak by checking
  in at slightly different times each day; 48h gives a full day of slack
  while still capping how long a pair can go dark.

**Consequences:**
- `partner_streaks.last_interaction_at` is `null` until a pending invite is
  accepted (streak isn't "live" yet). Acceptance itself counts as day 1
  (`current_streak` starts at 1, `last_interaction_at` stamped to the
  acceptance time) — mutual opt-in is treated as the first interaction, so
  a same-day check-in immediately after accepting is correctly a same-day
  idempotent no-op rather than double-counting day 1.
- A milestone bonus (`+10 thesdel_score` to both partners every 7th
  consecutive check-in day) was added as a small, self-contained call to
  `ProgressionService.add_score` (public service interface, never
  progression's repository) — this is the only cross-module integration
  built here.
- **Open follow-up (not built here):** if product wants a richer
  interaction model (e.g. multiple interaction types, partial credit,
  streak freezes/vacation days), that is a product/spec question to resolve
  before extending this, not something to guess at again.

---

## ADR-010: ARQ worker infrastructure, opaque-token TTLs, and reset-token storage shape

**Status:** Accepted, first-pass.

**Context:** `arq` was already a `pyproject.toml` dependency but no worker
process, job registry, or docker-compose service existed. Building it
required three judgment calls not pinned down elsewhere: (1) where the
`arq` job registry/enqueue helpers and the actual worker entrypoint live,
(2) the exact TTL for email-verification and password-reset opaque tokens
(docs/SECURITY.md only states a 15–60 min range), and (3) how reset/
verification tokens are stored.

**Decisions:**
1. **Module placement.** `app/shared/jobs.py` is a thin, dependency-free
   registry: it owns the ARQ pool (against the same `redis_url` as the
   rest of the app — no second Redis config) and exposes `enqueue_*`
   helper functions other modules call by job *name*. It deliberately does
   not import job *implementations* — that would make a shared module
   depend on a feature module. `app/auth/jobs.py` owns the actual send
   logic (idempotency check, retry/backoff, dead-letter) for the two jobs
   this task needs, inside `app/auth/`'s existing boundary. `app/worker.py`
   is the one place that imports both and wires them into `WorkerSettings`
   — the `arq` entrypoint (`arq app.worker.WorkerSettings`) — analogous to
   how `app/main.py` is the one place that imports every module's router.
   `docker-compose.yml` gets a `worker` service: same image/build as `api`,
   command overridden to run the ARQ worker instead of uvicorn.
2. **Token TTL: 60 minutes for email verification, 30 minutes for password
   reset.** Both within docs/SECURITY.md's 15–60 min range. Verification
   gets the longer end since signup itself is never blocked on it (no
   urgency, and mobile-first users may not check email immediately);
   password reset gets a shorter, mid-range TTL since a live reset flow is
   typically completed within minutes and a shorter window narrows the
   attack surface for a leaked/guessed reset link.
3. **Reset/verification token storage: one `auth_tokens` collection,
   `purpose` field distinguishing "email_verification" from
   "password_reset"**, rather than two separate collections or reusing
   `sessions`. Mirrors `SessionRepository`'s already-established pattern
   (opaque token, hashed at rest via the existing `hash_opaque_token`/
   `generate_opaque_token` helpers in `app/shared/security.py`, single-use,
   TTL-indexed) instead of inventing a second hashing/storage scheme. A
   single collection with a `purpose` field was chosen over two collections
   because the shape (user_id, token_hash, expiry, used_at) is identical
   and a query pattern already needs `(user_id, purpose)` regardless — see
   docs/DATABASE.md `auth_tokens`. Issuing a new token of a given purpose
   invalidates (`used_at`-stamps) any earlier outstanding token of that
   same purpose, so only the most recently issued link is ever valid.
4. **Retry/idempotency, literally per docs/ARCHITECTURE.md §8:** each email
   job checks the token document's `sent_at` marker before sending (a
   retried, at-least-once-delivered job is a no-op if a previous attempt
   already sent it) and retries with exponential backoff
   (`2, 4, 8, 16, 32` seconds) up to 5 attempts before dead-lettering via a
   structured error log — no new alerting infrastructure was built, per
   task scope.
5. **Enqueue failures never fail the calling request.** Per
   docs/ARCHITECTURE.md §7, `enqueue_*` in `app/shared/jobs.py` catches any
   exception, logs it, and returns — registration (and the other
   request-triggering-an-email endpoints) succeed even if Redis has a
   transient hiccup enqueuing the job.
6. **Resend integration is a thin, dependency-free wrapper
   (`app/shared/email.py`)** calling Resend's REST API directly via
   `httpx` (already installed — see `Dockerfile`, which keeps it in the
   production image) rather than adding the `resend` SDK package, per
   RULES.md #17 ("never introduce an unnecessary dependency"). If
   `resend_api_key` is unset (the local/test default), sending no-ops
   instead of raising, so dev/test never hard-fails on a missing key.

**Alternatives considered:**
- A single `app/shared/jobs.py` owning both the registry and every job
  implementation — rejected: as more modules gain background jobs, this
  file would accumulate unrelated business logic across module
  boundaries, exactly what RULES.md #19 ("never copy-paste business logic
  across modules... respecting module import boundaries") warns against.
- Reusing `sessions` for reset/verification tokens — rejected: different
  lifecycle (single-use vs. rotated-on-use, much shorter TTL, no
  `family_id`/reuse-detection concept), would overload one collection's
  schema with two different concerns.
- A single fixed TTL for both purposes — rejected: verification and reset
  have different urgency/risk profiles (see decision 2), so a single value
  would either be too short for a low-urgency verification email or too
  long for a live, higher-stakes password-reset link.

**Consequences:**
- The worker must be run as its own process (`docker compose up` now
  starts it as a `worker` service) — forgetting to run it means enqueued
  emails simply sit in the ARQ queue until a worker process consumes them;
  this doesn't fail any request, but should be checked in a deploy
  checklist.
- **Open follow-up (not built here):** the Backend Spec also mentions AI
  generation jobs, push notifications, and scheduled cleanup as ARQ
  consumers (docs/ARCHITECTURE.md §8) — those are separate, unbuilt
  features with their own job-registration needs when the time comes, not
  something to speculatively stub out here (RULES.md #23).

---

## ADR-011: Google Sign-In via ID-token verification, alongside email/password

**Status:** Accepted (confirmed by user 2026-08-23)

**Context:** Product wants "Sign in with Google" as an additional login
option on top of the existing email/password + refresh-token flow
(ADR-002), not a replacement for it.

**Alternatives considered:**
- Full OAuth 2.0 authorization-code flow (redirect to Google, exchange a
  code for tokens server-side) — rejected for now: requires a client
  secret and a redirect-URI dance that's more infrastructure than this
  needs. Google Identity Services' ID-token flow (frontend gets a signed
  JWT directly from Google, backend just verifies it) needs no client
  secret and no server-side redirect handling, at the cost of only
  working for "sign in," not broader Google API access — which is all
  that's needed here.
- Replacing email/password entirely — rejected per explicit product
  direction; email/password (ADR-002) stays as-is, Google is additive.

**Reason:** Matches the actual requirement (login, not broader Google API
scopes) with the least new infrastructure. The backend's only new
responsibility is verifying a token's signature, issuer, and audience
against Google's public keys — `google-auth`'s `verify_oauth2_token`
handles the key-fetching and signature check.

**Consequences:**
- `users.password_hash` is now nullable — a Google-only account has none.
  `AuthService.login` explicitly rejects a password attempt on such an
  account rather than passing `None` into `verify_password`.
- `users.google_id` (Google's stable `sub` claim) is added, with a sparse
  unique index — sparse because most accounts won't have one.
- Account linking: if a Google sign-in's email matches an existing
  password account, Google is linked to it automatically, but ONLY when
  Google itself reports that email as verified (`email_verified` claim).
  Skipping that check would let someone holding an unverified alias of
  another person's email hijack that account via Google sign-in — this
  guard is the entire reason `email_verified` is read from the claims at
  all.
- A Google-created account gets `email_verified_at` set immediately
  (Google already verified it) — no verification email is sent for that
  path, unlike registration via `AuthService.register`.
- `GOOGLE_CLIENT_ID` is required config — the backend rejects a token
  whose `aud` claim doesn't match it, which is what stops a valid ID
  token issued to some *other* app from being replayed against this one.
