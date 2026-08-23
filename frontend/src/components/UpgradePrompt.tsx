import type { Tier } from "../lib/api/types";

const TIER_LABEL: Record<Tier, string> = { free: "Free", premium: "Premium", pro: "Pro" };

export function UpgradePrompt({ requiredTier }: { requiredTier: Tier }) {
  return (
    <div
      role="alert"
      style={{
        padding: "2rem 1.5rem",
        textAlign: "center",
        color: "var(--color-text-secondary)",
      }}
    >
      <p style={{ fontSize: "var(--font-size-h3)", color: "var(--color-text-primary)" }}>
        Litheral is a {TIER_LABEL[requiredTier]} feature
      </p>
      <p>Upgrade to unlock this.</p>
      {/* Actual upgrade/billing flow is not yet implemented — see backend
          docs/DECISIONS.md ADR-007 (payment provider selection is open). */}
      <button type="button" style={{ background: "var(--color-primary)", color: "white", border: "none", borderRadius: "var(--radius-md)", padding: "0.75rem 1.5rem" }}>
        See plans
      </button>
    </div>
  );
}
