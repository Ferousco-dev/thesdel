# PRIVACY.md — Thesdel

Privacy is a product requirement here, not a footer page — this document
governs what's collected and why, independent of any specific legal
framework, since the target launch markets (Nigeria, Pakistan, Sri Lanka)
don't share a single unified privacy law equivalent to GDPR.

## 1. Data Collected and Why

| Data | Why collected | Source |
|---|---|---|
| Email, password hash | Account auth | `users` |
| Display name | Identify the user to classmates | `users` |
| Timetable entries (subject, day, time, location) | Core product function | `timetable_entries` |
| Class membership | Scope announcements/timetable sharing | `class_members` |
| Announcement content | Class communication feature | `announcements` |
| Study/routine inputs (subjects, priorities, exam dates, life routines) | Litheral generation (Premium/Pro) | `study_plans`, `routines` |
| AI usage records (feature, tokens/cost, timestamp) | Cost control + cap enforcement | `ai_usage_log` |
| Badges, score, rank | Progression/gamification feature | `user_badges`, `users.thesdel_score` |
| Partner streak interactions | Exploratory 1:1 feature | `partner_streaks` |
| Theme preference | UI personalization (Pro) | `users.theme_mode/theme_accent` |
| Device/session metadata (refresh token, device label) | Auth session management | `sessions` |
| Uploaded timetable images (import flow) | One-time parsing input | R2 object storage |
| Subscription/tier status | Billing enforcement | `users.tier`, billing webhook events |
| Device push token, platform | Deliver class-announcement/life-conflict push notifications | `device_tokens` |

**Nothing is collected "because it might be useful later."** Every field
above maps to a specific, currently-shipped feature. Any new field proposed
in future work should be checked against this table before being added.

## 2. Where Data Is Stored

- Primary data: MongoDB Atlas (region chosen with target-market latency and
  any applicable data-residency expectations in mind — not yet finalized,
  see Open Items).
- Uploaded images: Cloudflare R2.
- Backups: Atlas automated snapshots + independent export to R2 (see
  `DISASTER_RECOVERY.md`).
- Ephemeral data (rate-limit counters, cap counters, short-lived tokens):
  Redis, never treated as a permanent record.

## 3. Retention

| Data | Retention |
|---|---|
| `ai_usage_log` | TTL-expired after 13 months (audit trail only) |
| `sessions` | TTL-expired at token expiry; revoked (not deleted) on logout for reuse-detection purposes |
| Timetable/announcement content | Retained until user/class deletion |
| `user_badges`, `thesdel_score` | Currently spec'd as permanent — **pending resolution against account-deletion rights**, see §5 and `DECISIONS.md` ADR-006 |
| Uploaded timetable-import images | Deleted after successful parsing, or after a bounded TTL if parsing fails/is abandoned (not indefinitely retained) |
| `device_tokens` (FCM push token, platform) | Retained until explicitly unregistered by the user or overwritten by another user re-registering the same physical device (upsert-by-token) — no TTL, since a stale-but-not-yet-invalid token is harmless and FCM itself reports dead tokens for pruning (see `app/notifications/jobs.py`) |

## 4. Third-Party Processors

| Processor | Data shared | Purpose |
|---|---|---|
| LLM API provider (TBD) | Timetable-import text/image content (for parsing only) | Litheral import parsing |
| Resend | Email address, email content | Transactional email delivery |
| FCM (Google) | Device push token | Push notifications |
| Payment provider(s), market-specific | Billing/subscription data (not payment credentials — handled by the provider directly) | Subscription billing |
| Cloudflare | Request metadata (IP, headers) | CDN/WAF/DDoS protection |
| Ad network (Free tier) | Ad-eligibility flag, general (not timetable) usage context | Ad serving — client-side rendering, server only signals eligibility |

**Ad network boundary:** the server exposes only an ad-eligibility flag
(tier === free); actual ad content/targeting is handled client-side by the
ad SDK. No timetable, class, or academic content is passed to the ad
network. This boundary is worth re-confirming against whichever ad SDK is
selected, since ad SDKs commonly request broader data access by default.

## 5. Data Subject Rights (Export / Deletion)

- **Export:** users can request their own data (timetable entries,
  announcements they've posted, study/routine inputs, badges/score) in a
  structured export — not yet implemented, scoped as a Roadmap item.
- **Deletion:** account deletion removes auth credentials, session records,
  and PII-bearing content (display name, timetable entries owned by the
  user). **Open question:** whether `thesdel_score` and `user_badges`
  survive deletion in anonymized/aggregate form (to preserve
  leaderboard/season integrity) or are hard-deleted — see `DECISIONS.md`
  ADR-006. V1 deletion flow will implement the PII-removal portion
  regardless of how that question resolves, so deletion isn't blocked on
  it.

## 6. Analytics / Tracking

No third-party analytics/tracking SDK is currently specified in either
source document. If one is added later (e.g. for product usage metrics),
it goes through the same "why collected" test as §1 and gets added to this
document before implementation — not silently bundled into a client build.

## 7. Cookies

The API is a JSON REST API; the frontend is a mobile-first React app.
Cookie usage, if any (e.g. for a web-session component), will use the most
privacy-preserving defaults (`HttpOnly`, `Secure`, minimal scope) and any
non-essential cookie (analytics, marketing) requires explicit consent per
the master prompt's baseline privacy rule — none currently planned.

## 8. Sensitive/Minors Consideration

Neither source spec addresses age or minors explicitly. Target markets are
described as students (secondary/university), which may include minors in
some markets. This is flagged as an **open item requiring product/legal
input** before launch — not resolved by assumption in this document. See
Phase 0 audit and `RESEARCH.md` #10.

## 9. Open Items

- Data-residency expectations per market (NG/PK/LK) — may affect MongoDB
  Atlas region selection.
- Minors/age-gating policy.
- Final resolution of ADR-006 (score/badge retention vs. deletion rights).
- Formal privacy policy document (user-facing, legally reviewed) — this
  file is the engineering-facing source of truth it should be generated
  from, not a replacement for it.
