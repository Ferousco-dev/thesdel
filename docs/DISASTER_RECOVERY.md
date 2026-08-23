# DISASTER_RECOVERY.md — Thesdel

## 1. Backup Strategy

- **Primary:** MongoDB Atlas automated continuous/snapshot backups
  (available even on shared/low tiers; upgraded to more frequent
  point-in-time recovery as budget allows once real usage justifies it —
  not preemptively, per the cost-sensitivity requirement).
- **Secondary/independent copy:** periodic (daily) export of a full DB dump
  to Cloudflare R2, encrypted at rest, kept outside Atlas's own control
  plane — protects against an Atlas account-level failure or credential
  compromise, not just data corruption.
- **Encryption:** backups encrypted at rest (Atlas default + R2
  server-side encryption for the exported copy).
- **Access control:** backup access restricted to a minimal set of
  credentials, separate from day-to-day application database credentials
  where the provider supports it.

## 2. Retention

- Atlas snapshots: retained per the provider's default window for the tier
  in use (documented explicitly once the specific Atlas tier is chosen —
  not assumed here).
- R2 export copies: rolling 30-day retention initially, revisited once
  actual restore-testing cadence and storage cost are known.

## 3. Backup Verification

A backup that has never been restored is not a verified backup. Monthly
restore-drill: restore the most recent R2 export into a scratch/staging
MongoDB instance and run a basic integrity check (collection counts, a
sample of documents against expected shape) — logged, not just performed
ad hoc.

## 4. Recovery Objectives

- **RPO (Recovery Point Objective):** ≤24 hours, bounded by the daily R2
  export cadence; Atlas's own continuous backup (if enabled at the chosen
  tier) may provide a tighter RPO for the primary-restore path.
- **RTO (Recovery Time Objective):** target ≤4 hours for a full restore
  from the R2 export path, assuming a fresh Atlas cluster provisioned and
  the application redeployed against it. This is a target to validate
  during the first restore drill, not an assumption to leave untested.

## 5. Recovery Procedures by Scenario

### Database corruption
1. Identify the corruption's onset time from structured logs
   (`request_id`-correlated errors are the first signal, per
   `OBSERVABILITY.md`).
2. Restore the most recent clean Atlas snapshot or R2 export predating the
   corruption into a new cluster/instance.
3. Replay any recoverable writes between the restore point and the
   incident (if application logs/audit trail make this possible) — accept
   data loss for the gap if not.
4. Point the application at the restored instance via configuration, not a
   code change.
5. Post-incident: root-cause the corruption before resuming normal
   operation.

### Accidental deletion (user data, a collection, or a whole database)
1. Same restore path as above, scoped to the smallest recoverable unit
   (a single collection restore from snapshot, where the provider
   supports selective restore, rather than a full-instance restore).
2. Cross-reference audit logs (`SECURITY.md` §10) to identify what was
   deleted and by what action, before restoring, to avoid re-deleting via
   the same bug/action.

### Credential compromise (DB, Redis, LLM API key, payment provider key,
R2, Resend, etc.)
1. Rotate the affected credential immediately via the environment-variable
   strategy (`SECURITY.md` §7) — every secret is swappable without a code
   change, only a config/deploy change.
2. Revoke all active sessions if the compromised credential could have
   exposed auth data (§`SECURITY.md` §2).
3. Audit logs and provider-side access logs (where available) reviewed for
   unauthorized activity during the exposure window.
4. Notify affected users if the compromise resulted in unauthorized data
   access — specific notification obligations per market are a
   product/legal decision to formalize (see `SECURITY.md` §11 and
   `PRIVACY.md` open items).

### Application bug causing bad writes
1. Identify the bug's deploy window via deployment history.
2. Roll back the deploy (see `ARCHITECTURE.md`/CI-CD rollback
   consideration).
3. Restore affected data from the nearest clean backup, or write a
   targeted, reviewed remediation script if the bad-write pattern is
   well-understood and narrow enough that a full restore would lose more
   good data than it fixes — this decision is made deliberately per
   incident, never defaulted to "just run a fix script" without review.

### Infrastructure failure (Atlas region outage, Redis provider outage,
Cloudflare outage)
- **Atlas outage:** no in-house mitigation beyond the provider's own
  multi-AZ replica set; a cross-region failover is a future consideration
  once budget/scale justify a multi-region Atlas tier — not assumed at
  launch.
- **Redis outage:** application continues in the degraded mode specified
  in `ARCHITECTURE.md` §7 (fail closed for security-critical paths, fail
  open with a conservative fallback for reads) — this is designed
  in-application specifically so a non-critical cache/counter outage
  doesn't take the whole app down, per the master prompt's explicit
  requirement.
- **Cloudflare outage:** origin is still reachable directly if Cloudflare's
  proxy layer fails, as a documented fallback DNS path — to be configured
  once the production domain is set up, not assumed to exist by default.

## 6. Open Items

- Specific Atlas tier and its included backup window — to be finalized
  when infrastructure is provisioned (Phase 6 of the roadmap).
- Formal notification-obligation procedure per market — pending legal
  input, tracked in `PRIVACY.md`.
