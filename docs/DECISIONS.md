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
