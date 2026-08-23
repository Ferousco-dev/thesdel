"""Migration 0001: seed a representative badge catalog for app/progression/.

IMPORTANT — scope note: the Backend Spec references ~17 badge families and
~225 total badges, but no exact badge names/criteria for that full catalog
are documented anywhere available to this codebase. Hand-authoring 225
invented badge definitions here would be silently inventing spec content,
which RULES.md and this task explicitly warn against. Instead, this
migration seeds a small, clearly-illustrative set (a handful per family,
covering different criteria_types) so the award mechanism
(app/progression/service.py: evaluate_and_award / award_badge) is
exercised end-to-end. Populating the full ~225-badge catalog is a follow-up
CONTENT task (needs the actual badge copy/criteria from product/design),
not an engineering blocker — see docs/DECISIONS.md.

Idempotent per docs/DATABASE.md §5: safe to run more than once. Records
itself in `schema_migrations` and no-ops on a second run. Never touches an
existing `badges` document — only inserts the seed set if this migration id
hasn't run yet.

Run (from repo root): python migrations/0001_seed_progression_badges.py
"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.shared.db import close_client, get_db  # noqa: E402

MIGRATION_ID = "0001_seed_progression_badges"

# family -> list of (name, criteria_type, criteria_value)
# Illustrative only. Each family gets 2-3 badges spanning different
# criteria_types so evaluate_and_award() is exercised for count-based,
# streak-based, and milestone-style criteria.
_SEED_BADGES: dict[str, list[tuple[str, str, Any]]] = {
    "onboarding": [
        ("Welcome Aboard", "signup_completed", True),
        ("Profile Complete", "profile_fields_filled", 5),
    ],
    "timetable": [
        ("First Timetable", "timetable_entries_created", 1),
        ("Fully Scheduled", "timetable_entries_created", 20),
    ],
    "classes": [
        ("Class Joined", "classes_joined", 1),
        ("Class Rep", "classes_created", 1),
    ],
    "announcements": [
        ("First Post", "announcements_posted", 1),
        ("Active Voice", "announcements_posted", 10),
    ],
    "study_litheral": [
        ("Study Plan Generated", "study_plans_generated", 1),
        ("Study Regular", "study_sessions_completed", 10),
    ],
    "life_litheral": [
        ("Life Scheduled", "life_schedules_generated", 1),
    ],
    "routines": [
        ("Routine Set", "routines_created", 1),
        ("Routine Master", "routines_created", 6),
    ],
    "usage_engagement": [
        ("Power User Week", "consecutive_active_days", 7),
    ],
    "streaks": [
        ("Streak Starter", "partner_streak_days", 3),
        ("Streak Champion", "partner_streak_days", 30),
    ],
    "score_milestones": [
        ("First Points", "thesdel_score_reached", 100),
        ("Rising Star", "thesdel_score_reached", 1000),
    ],
    "seasons": [
        ("Season Participant", "seasons_participated", 1),
    ],
    "consistency": [
        ("Weekly Regular", "weeks_active", 4),
    ],
    "billing": [
        ("Went Premium", "tier_upgraded_to", "premium"),
        ("Went Pro", "tier_upgraded_to", "pro"),
    ],
    "referrals": [
        ("First Referral", "referrals_completed", 1),
    ],
    "exploration": [
        ("Explorer", "features_used", 5),
    ],
    "feedback": [
        ("Feedback Given", "feedback_submitted", 1),
    ],
    "loyalty": [
        ("One Month In", "days_since_signup", 30),
        ("One Year In", "days_since_signup", 365),
    ],
}


async def run() -> None:
    db = get_db()

    already_ran = await db.schema_migrations.find_one({"_id": MIGRATION_ID})
    if already_ran is not None:
        print(f"{MIGRATION_ID}: already applied, skipping.")
        return

    inserted = 0
    for family, badges in _SEED_BADGES.items():
        for name, criteria_type, criteria_value in badges:
            existing = await db.badges.find_one({"family": family, "name": name})
            if existing is not None:
                continue
            await db.badges.insert_one(
                {
                    "family": family,
                    "name": name,
                    "criteria_type": criteria_type,
                    "criteria_value": criteria_value,
                }
            )
            inserted += 1

    await db.schema_migrations.insert_one(
        {"_id": MIGRATION_ID, "applied_at": datetime.now(UTC), "badges_inserted": inserted}
    )
    print(
        f"{MIGRATION_ID}: inserted {inserted} illustrative badges "
        f"across {len(_SEED_BADGES)} families."
    )


async def main() -> None:
    try:
        await run()
    finally:
        await close_client()


if __name__ == "__main__":
    asyncio.run(main())
