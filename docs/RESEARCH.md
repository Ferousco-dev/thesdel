# RESEARCH.md — Thesdel

Research performed before implementation, per the Phase 0/1 audit. This is a living
document — add an entry whenever a technical decision is backed by research, before
that decision is coded.

Format per entry: **Source → Finding → Why it matters → Architectural impact**

---

## 1. Original spec assumed Supabase (Postgres + Auth + Storage)

- **Source:** `Thesdel_Backend_Spec.docx` §2–3, provided by product.
- **Finding:** The original design leaned on Supabase for Postgres, Auth, and
  Storage, with `users.id` explicitly documented as "Supabase auth user id."
  PostgREST gave implicit CRUD; Supabase Auth gave password hashing, session
  tokens, email verification, and password reset for free.
- **Why it matters:** Swapping to MongoDB + FastAPI removes all of that for free
  — auth, session management, and every CRUD endpoint must now be designed and
  built explicitly.
- **Architectural impact:** New `auth` module scoped in `ARCHITECTURE.md`;
  new `AUTH` section in `SECURITY.md`; sized as its own implementation phase
  (Roadmap Phase 2) rather than bundled into general backend setup.

## 2. Vector search (pgvector) — not currently justified

- **Source:** Backend Spec §5.2 ("V1 should avoid building an adaptive ML
  model... use an LLM call only where natural-language flexibility genuinely
  helps... not for the core time-slotting math").
- **Finding:** Nothing in either spec performs semantic/embedding search.
  Litheral's core scheduling is a constraint/bin-packing problem, not a
  retrieval problem. The only LLM use case named is structuring a
  pasted/imported timetable into structured data — a one-shot extraction task,
  not a search task.
- **Why it matters:** MongoDB Atlas Vector Search (or any vector DB) would be
  an unjustified dependency per the master prompt's overengineering rule.
- **Architectural impact:** Vector search excluded from v1 infrastructure.
  Revisit only if a genuine semantic-search feature is scoped (e.g. "find
  classes like this one" or fuzzy timetable matching beyond LLM extraction) —
  logged as a deferred decision in `DECISIONS.md`.

## 3. MongoDB transactions require a replica set

- **Source:** MongoDB official documentation (multi-document transactions,
  available since MongoDB 4.0 on replica sets, since 4.2 on sharded clusters).
- **Finding:** Atlas's free (M0) and shared tiers provision a 3-node replica
  set by default, so multi-document transactions are available without
  upgrading to a dedicated cluster.
- **Why it matters:** Two operations in this domain need atomicity that
  Postgres gave implicitly: (a) class join + `member_count` increment, and
  (b) AI-usage-cap check-then-log. Confirms transactions are usable at the
  free-tier budget the product requires.
- **Architectural impact:** `DATABASE.md` documents where transactions are
  used vs. where a simpler atomic operation (`$inc`, `findOneAndUpdate`)
  suffices instead of reaching for a transaction by default.

## 4. Redis atomic counters as the AI-usage-cap primitive

- **Source:** Redis official documentation (`INCR`, `EXPIRE`, atomicity
  guarantees of single-command operations); Backend Spec §6 ("Caps are
  enforced server-side... never client-enforced only").
- **Finding:** `INCR` on a key scoped to `user_id:feature:billing_period`,
  combined with `EXPIRE` set to the billing-period boundary, gives an atomic,
  race-free cap check-and-increment in a single round trip — cheaper and
  simpler than a Mongo transaction for this specific read-then-write pattern,
  and reusable as the same primitive for general rate limiting.
- **Why it matters:** The backend spec calls the usage-cap system "the single
  most important cost-control mechanism in the whole backend." A check that
  isn't atomic under concurrent duplicate-tap requests defeats the cap
  entirely.
- **Architectural impact:** `usage` module implemented against Redis, not
  Mongo, for the live counter; `ai_usage_log` in Mongo remains the durable
  audit trail (written after the Redis check passes), not the enforcement
  point itself.

## 5. Argon2id for password hashing

- **Source:** OWASP Password Storage Cheat Sheet (current guidance recommends
  Argon2id as the first choice, bcrypt as fallback).
- **Finding:** Argon2id is OWASP's current top recommendation, resistant to
  both GPU cracking and side-channel attacks, and has mature Python bindings
  (`argon2-cffi`) compatible with FastAPI/async code.
- **Why it matters:** Since Supabase Auth's hashing is no longer inherited,
  this is a first-class decision, not an assumption.
- **Architectural impact:** `auth` module password storage uses Argon2id;
  documented in `SECURITY.md` under Authentication.

## 6. JWT access token + server-side refresh token

- **Source:** OWASP JWT Cheat Sheet; OWASP Session Management Cheat Sheet.
- **Finding:** A bare stateless JWT cannot be revoked before expiry, which
  breaks "logout everywhere" and post-password-change session invalidation —
  both reasonable expectations the spec implies via "multiple devices."
  Short-lived access JWT (~15 min) + longer-lived opaque refresh token stored
  server-side (revocable, rotated on use, reuse-detection for theft) is the
  standard mitigation.
- **Why it matters:** This is one of the master prompt's explicit
  stop-conditions ("changing authentication architecture") — flagged to the
  user for sign-off before implementation (see `DECISIONS.md` #1).
- **Architectural impact:** `auth` module stores refresh tokens (hashed) in a
  `sessions` collection with device metadata; access tokens are never
  persisted server-side.

## 7. Cloudflare role — proxy/WAF only, not compute

- **Source:** Cloudflare product documentation (Workers, WAF, R2, DNS/CDN).
- **Finding:** The product's compute and cost-sensitivity requirements are
  satisfied by Cloudflare as a DNS/CDN/WAF proxy in front of the FastAPI app
  and R2 for object storage. Workers, KV, Queues, and Durable Objects have no
  requirement pulling them in for this monolith.
- **Why it matters:** Avoids the "fake microservices" and overengineering
  anti-patterns the master prompt explicitly warns against.
- **Architectural impact:** Cloudflare scoped to DNS/CDN/WAF + R2 only in
  `ARCHITECTURE.md`.

## 8. Background job pattern for a small FastAPI monolith

- **Source:** ARQ (Redis-backed async job queue, asyncio-native, documented
  for FastAPI-style applications) vs. Celery (broker-agnostic, heavier
  operational footprint: separate worker fleet, broker, result backend).
- **Finding:** ARQ requires only Redis (already in the stack for caps/rate
  limiting) and integrates natively with FastAPI's async model, avoiding a
  second broker (RabbitMQ) that Celery would typically pair with in
  production.
- **Why it matters:** AI generation calls, email sending, and push
  notifications must not block the request/response cycle, but the team size
  and budget don't justify Celery/Kafka-scale infrastructure.
- **Architectural impact:** Background jobs implemented via ARQ against the
  same Redis instance; documented in `ARCHITECTURE.md` under Background Jobs.

## 9. Payment provider landscape — NG/PK/LK

- **Source:** Not yet researched — flagged as an explicit open item in both
  the original Backend Spec (§10) and the Phase 0 audit.
- **Finding:** Pending. Each market has different dominant local rails
  (e.g. Nigeria: Paystack/Flutterwave; Pakistan: JazzCash/Easypaisa or
  card-based; Sri Lanka: local bank gateways) — a single global provider
  assumption (e.g. Stripe alone) will not cover all three markets.
- **Why it matters:** Billing implementation (Roadmap Phase 6) is blocked on
  this without a placeholder abstraction.
- **Architectural impact:** `billing` module designed against a
  provider-agnostic webhook interface (signature verification + event
  idempotency) so a specific provider can be plugged in per market without
  changing the tier-mutation logic. Provider selection remains an open
  question in `DECISIONS.md`.

## 10. Data minimization / minors consideration

- **Source:** Not yet researched — flagged as an open item in the Phase 0
  audit (§17.3 equivalent).
- **Finding:** Neither spec document addresses minors or a specific privacy
  framework. Target markets (NG/PK/LK) do not have a single unified law
  equivalent to GDPR/COPPA that automatically applies.
- **Why it matters:** Affects `PRIVACY.md` retention/deletion policy design
  and whether age-gating or parental-consent flows are required.
- **Architectural impact:** V1 designed with data minimization defaults
  (collect only what's specified in the data model, no speculative fields)
  and an account-deletion path that's technically feasible even before the
  specific legal requirement is confirmed.
