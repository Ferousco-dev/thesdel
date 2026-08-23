# DATABASE.md — Thesdel (MongoDB)

Domain-modeled, not a literal port of the original Postgres schema. See
`RESEARCH.md` and the Phase 0 audit for the reasoning behind each
collection's shape.

## 1. Collections

### `users`
```
_id: ObjectId
email: string, unique
password_hash: string          # Argon2id
email_verified_at: datetime | null
display_name: string
tier: "free" | "premium" | "pro"
tier_renewed_at: datetime
theme_mode: "light" | "dark"
theme_accent: string | null     # Pro-only; null = default Thesdel orange
thesdel_score: int              # permanent, always-increasing (see DECISIONS ADR-006)
rank: string
is_verified: bool               # derived from active subscription, see billing
created_at: datetime
```
**Indexes:** unique on `email`.

### `classes`
```
_id: ObjectId
name: string
created_by: ObjectId -> users._id
join_code: string, unique
member_count: int               # denormalized; kept in sync via app-level
                                 # atomic $inc on join/leave, not a DB trigger
                                 # (Mongo has no trigger equivalent)
created_at: datetime
```
**Indexes:** unique on `join_code`.

### `class_members`
```
_id: ObjectId
class_id: ObjectId -> classes._id
user_id: ObjectId -> users._id
role: "rep" | "member"
joined_at: datetime
```
**Indexes:** unique compound `{class_id, user_id}` (replaces Postgres
composite PK); secondary index `{user_id}` for "which classes is this user
in"; secondary index `{class_id}` for "who's in this class."

**Why not embed members in `classes`:** class sizes are expected to scale
"into the hundreds" per the Backend Spec — an embedded array risks the
16MB document cap and unbounded-array growth explicitly called out as an
anti-pattern.

### `timetable_entries`
```
_id: ObjectId
owner_type: "user" | "class"
owner_id: ObjectId              # user_id or class_id depending on owner_type
subject: string
day_of_week: int                # 0-6
start_time: string              # HH:MM, stored as string or minutes-since-midnight
end_time: string
location: string | null
recurrence: string | null       # e.g. "weekly", null for one-off
created_at: datetime
```
**Indexes:** compound `{owner_type, owner_id, day_of_week}` — serves the
dominant query (render one owner's week).

### `announcements`
```
_id: ObjectId
class_id: ObjectId -> classes._id
posted_by: ObjectId -> users._id
content: string
pinned: bool
created_at: datetime
```
**Indexes:** compound `{class_id, pinned, created_at}` — serves the feed
query (pinned-first, recency-ordered, scoped to joined classes).

### `study_plans` (Premium)
```
_id: ObjectId
user_id: ObjectId -> users._id
subject: string                 # pulled from timetable_entries at generation time
priority: int | null
exam_date: date | null
day_of_week: int
start_time: string
end_time: string
generated_at: datetime
```
**Indexes:** compound `{user_id, generated_at}`.

**Access rule:** only the `litheral/study` module may query this
collection's repository. Enforced by module import boundaries (see
`ARCHITECTURE.md` §2), not by a query-level filter alone.

### `routines` (Pro)
```
_id: ObjectId
user_id: ObjectId -> users._id
label: "Church" | "Gym" | "Work" | "Sleep" | "Meals" | "Personal"
days: int[]
start_time: string
end_time: string
is_flexible: bool
```
**Indexes:** `{user_id}`.

**Isolation rule (critical, spec-mandated):** the Premium code path
(`litheral/study`) must have zero import path to this collection's
repository. This is enforced structurally, not by a runtime check that
could be bypassed by a future change — see `ARCHITECTURE.md` §2 and
`RULES.md`.

### `life_schedule_blocks` (Pro, generated)
```
_id: ObjectId
user_id: ObjectId -> users._id
source_type: "class" | "study" | "routine"
source_id: ObjectId
day_of_week: int
start_time: string
end_time: string
conflict_flag: bool             # conflicts written, never silently dropped
```
**Indexes:** compound `{user_id, day_of_week}`.

### `ai_usage_log`
```
_id: ObjectId
user_id: ObjectId -> users._id
feature: "study_generate" | "study_regenerate" | "life_generate" | "life_adjust"
tokens_used: int | null
cost_estimate: float | null
status: "attempted" | "succeeded" | "failed"
created_at: datetime
```
**Indexes:** compound `{user_id, feature, created_at}` — serves the
cap-check-by-window query directly. **TTL index on `created_at`** (e.g.
expire after 13 months) to keep this write-heavy collection bounded — it is
an audit trail, not the live enforcement point (Redis is; see
`ARCHITECTURE.md` §7 and `DECISIONS.md` ADR-004).

### `badges`
```
_id: ObjectId
family: string                  # one of ~17 families
name: string
criteria_type: string
criteria_value: any
```

### `user_badges`
```
_id: ObjectId
user_id: ObjectId -> users._id
badge_id: ObjectId -> badges._id
earned_at: datetime             # permanent, never deleted — see DECISIONS ADR-006
```
**Indexes:** unique compound `{user_id, badge_id}`.

### `seasons`
```
_id: ObjectId
start_date: date
end_date: date                  # ~3-month cadence
```

### `partner_streaks` (exploratory)
```
_id: ObjectId
user_a: ObjectId -> users._id   # normalized: user_a < user_b lexically,
user_b: ObjectId -> users._id   # so a pair is never creatable in both directions
current_streak: int
last_interaction_at: datetime
status: "pending" | "active"    # mutual opt-in required — see SECURITY.md
```
**Indexes:** unique compound `{user_a, user_b}`.

### `sessions` (new — required by ADR-002, not in original spec)
```
_id: ObjectId
user_id: ObjectId -> users._id
refresh_token_hash: string       # unique — the token value, hashed at rest
family_id: string                # groups tokens from one rotation chain;
                                  # reuse of a rotated-away token revokes the
                                  # whole family (theft signal, see SECURITY.md)
device_label: string | null
created_at: datetime
expires_at: datetime
revoked_at: datetime | null
```
**Indexes:** `{user_id}`, `{family_id}`, unique `{refresh_token_hash}`, TTL
index on `expires_at`.

## 2. Query Patterns and Their Indexes — Summary Table

| Query | Index |
|---|---|
| Render a user's/class's week | `timetable_entries {owner_type, owner_id, day_of_week}` |
| List a user's classes | `class_members {user_id}` |
| List a class's members | `class_members {class_id}` |
| Announcement feed for a class | `announcements {class_id, pinned, created_at}` |
| AI cap check for current period | `ai_usage_log {user_id, feature, created_at}` (backstop; live check is Redis) |
| Badge shelf for a user | `user_badges {user_id, badge_id}` unique compound doubles as lookup index |
| Streak lookup for a pair | `partner_streaks {user_a, user_b}` unique compound |
| Session lookup on refresh | `sessions {user_id}` |

Every index above exists because it serves a named query pattern in this
table — no index is added speculatively (per `RULES.md`: never add a
database query without considering indexes, and the inverse — never add an
index without a query that needs it).

## 3. Concurrency / Transactions

MongoDB Atlas provisions a replica set even on free/shared tiers, making
multi-document transactions available (see `RESEARCH.md` #3). Used only
where a simpler atomic operation is insufficient:

- **Class join:** `class_members` insert + `classes.member_count` `$inc` —
  wrapped in a transaction to avoid drift if the process crashes
  mid-operation. (Not used at all on the read path — `member_count` is
  read as a denormalized field, never recomputed live, per the Backend
  Spec's explicit guidance.)
- **AI usage cap:** enforced via Redis atomic counter (`DECISIONS.md`
  ADR-004), not a Mongo transaction — `ai_usage_log` write happens after
  the Redis check passes, as an audit record, not the enforcement point.
- **Badge award:** `findOneAndUpdate` with `$addToSet`-style uniqueness
  guard (or the unique compound index on `user_badges` catching a duplicate
  insert) — a full transaction is unnecessary here since it's a single
  collection.

## 4. Soft Deletion / Retention

- `announcements`, `timetable_entries`: hard-deleted on user action (no
  retention requirement identified).
- `ai_usage_log`: TTL-expired after 13 months (audit trail, not permanent
  record).
- `user_badges`, `thesdel_score`: currently "permanent, never deleted" per
  spec — **pending resolution against account-deletion requirements**, see
  `DECISIONS.md` ADR-006 and `PRIVACY.md`.
- `sessions`: TTL-expired at `expires_at`; explicitly revoked (not deleted)
  on logout, so a reused stolen refresh token can still be reuse-detected
  before the TTL clears it.

## 5. Migrations

Schema versioning is handled via a lightweight migration script pattern
(no ORM-level auto-migration, since Mongo has no schema to migrate in the
SQL sense) — each migration is a small, idempotent script under
`migrations/`, applied and recorded in a `schema_migrations` collection.
Every migration is reviewed for destructive potential per `RULES.md`
("never make destructive database changes... without explicit
authorization").

## 6. Backups / Restore

See `DISASTER_RECOVERY.md` for full procedure. Summary: Atlas automated
snapshots + periodic export to R2 as an independent copy outside the
primary provider's control plane.
