# OBSERVABILITY.md — Thesdel

## 1. Logging

Structured JSON logs, one line per event, at every layer (HTTP request →
service → repository/queue → background worker → external provider call).
No PII in logs — user IDs and resource IDs are logged, not timetable
content, announcement text, email addresses, or names.

Every log line carries:
- `request_id` — assigned at the edge (Cloudflare/FastAPI middleware), threaded
  through every downstream call including enqueued background jobs.
- `user_id` (if authenticated) — not the user's email/name.
- `event` — a stable, documented event name (e.g.
  `ai_generation.attempted`, `class.joined`, `auth.login_failed`).
- `timestamp`, `level`.

## 2. Correlation IDs

`request_id` is generated once per inbound HTTP request and passed into any
ARQ job enqueued as part of handling that request, so a single user action
(e.g. "generate study plan") is traceable end-to-end: HTTP request →
tier/cap check → job enqueue → worker execution → LLM API call → DB write →
push notification, all under one `request_id`. This is what makes the
failure-first requirement ("can I understand what happened") answerable in
practice, not just in principle.

## 3. Metrics

- Request rate, latency (p50/p95/p99), error rate — per endpoint.
- AI generation: attempt rate, success/failure rate, latency, cost-per-call
  (from `ai_usage_log`) — this is the single most cost-sensitive metric per
  the Backend Spec's own priority ordering, so it gets dashboard priority.
- Cap-rejection rate — a spike here indicates either abuse or caps set too
  low relative to real usage; both are actionable signals.
- Redis/Mongo connection health, queue depth, job failure/dead-letter rate.
- Rate-limit rejection rate per endpoint class.

## 4. Health Checks

- `GET /healthz` — liveness: process is running, returns `200` immediately.
- `GET /readyz` — readiness: checks MongoDB connectivity and Redis
  connectivity, returns `503` if either is down. Used by the deployment
  platform to gate traffic, not by end users.
- Queue health: ARQ worker heartbeat monitored separately (dead workers
  should page, not silently stop processing jobs).
- External provider health (LLM API, Resend, FCM): not polled directly, but
  surfaced via the error-rate metrics on calls to them (§3) — polling a
  third party's health endpoint speculatively adds no value here.

## 5. Error Tracking

All unhandled exceptions and any explicitly-logged `error` level event are
captured with the request/correlation ID attached, so an error tracker
entry can be cross-referenced back to the full structured log trail for
that request. Stack traces live only in the error tracker / internal logs
— never in an API response (see `API.md` §4).

## 6. Alerts

Alert-worthy conditions (specific thresholds to be tuned once real traffic
data exists, per the same "config, not hardcoded, tune after real data"
principle applied to AI caps):
- Error rate above baseline on any endpoint.
- `readyz` failing (DB/Redis down).
- AI generation failure rate spike (signals LLM provider issues before
  users report it).
- Cap-rejection rate spike (signals abuse or a cap set too low).
- ARQ dead-letter rate above zero sustained (jobs are failing after all
  retries — silent data/notification loss otherwise).
- Webhook signature-verification failure spike (signals a forged webhook
  attempt or a provider integration break).

## 7. What Is Deliberately Not Instrumented Yet

Full APM tracing across every internal function call, client-side session
replay, and speculative business-metric dashboards are not built until a
concrete need exists — matching the master prompt's instruction to avoid
premature/blind instrumentation. The above covers what's needed to answer
"can I understand what happened" for this specific system's actual failure
modes.
