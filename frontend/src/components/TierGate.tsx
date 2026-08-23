import type { ReactNode } from "react";

import { useAuth } from "../lib/auth/useAuth";
import type { Tier } from "../lib/api/types";

const TIER_RANK: Record<Tier, number> = { free: 0, premium: 1, pro: 2 };

/** Per Frontend Spec §3: tier-gated tabs/features stay visible to Free
 * users — tapping opens an upgrade prompt rather than being hidden. This
 * mirrors the backend's server-side tier check (never trust this alone —
 * every gated backend endpoint re-checks tier itself, see backend
 * docs/SECURITY.md §4). This component is a UX affordance, not a security
 * boundary — don't treat it as one. */
export function TierGate({
  requiredTier,
  children,
  upgradePrompt,
}: {
  requiredTier: Tier;
  children: ReactNode;
  upgradePrompt: ReactNode;
}) {
  const { user } = useAuth();
  const currentRank = user ? TIER_RANK[user.tier] : -1;

  if (currentRank >= TIER_RANK[requiredTier]) {
    return <>{children}</>;
  }
  return <>{upgradePrompt}</>;
}
