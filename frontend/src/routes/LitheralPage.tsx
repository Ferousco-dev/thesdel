import { TierGate } from "../components/TierGate";
import { UpgradePrompt } from "../components/UpgradePrompt";

// Placeholder for Frontend Spec §5-6: study plan generation (Premium) and
// life organizer (Pro). TierGate demonstrates the required pattern — every
// gated screen/action must be wrapped this way, matching how the backend
// gates the same features server-side (see backend docs/API.md §3).
export function LitheralPage() {
  return (
    <TierGate requiredTier="premium" upgradePrompt={<UpgradePrompt requiredTier="premium" />}>
      <div style={{ padding: "1.5rem" }}>
        <h2 style={{ fontSize: "var(--font-size-h2)" }}>Litheral</h2>
        <p style={{ color: "var(--color-text-secondary)" }}>
          TODO: study plan generation UI (§5.1-5.3), and — nested behind a
          "pro" TierGate — the life organizer UI (§6.1-6.4). See
          lib/api/endpoints.ts for generateStudyPlan/listStudyPlan/
          regenerateStudyBlock and the routines/life equivalents.
        </p>
      </div>
    </TierGate>
  );
}
