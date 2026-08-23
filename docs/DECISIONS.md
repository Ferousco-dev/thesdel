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

## ADR-006: Account deletion / permanent-badge tension — deferred

**Status:** Open — not blocking early roadmap phases, must resolve before
the `progression` module (Roadmap Phase 7) or any account-deletion feature
ships.

**Context:** Backend Spec describes `thesdel_score` as "permanent,
always-increasing" and `user_badges` as "permanent, never deleted." This
conflicts with a standard account-deletion / right-to-erasure requirement.

**Alternatives considered:**
- Hard-delete everything on account deletion, including score/badges.
- Anonymize (strip PII, keep aggregate score/badge records under a deleted
  placeholder identity) — preserves leaderboard/season integrity.
- Defer deletion entirely until a specific market's legal requirement
  forces the decision.

**Reason:** Not yet decided — logged as an explicit open question back to
the product owner (see Phase 0 audit §17.3).

**Consequences:** V1 account-deletion flow will be scoped narrowly (PII
removal, auth invalidation) without committing to a score/badge policy
until this is resolved.

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
