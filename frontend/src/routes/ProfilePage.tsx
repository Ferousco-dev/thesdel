import { useAuth } from "../lib/auth/useAuth";

// Placeholder for Frontend Spec §7: Thesdel Score, rank, badges, season
// progress, contribution-graph activity view, partner streaks.
export function ProfilePage() {
  const { user, logout } = useAuth();

  return (
    <div style={{ padding: "1.5rem" }}>
      <h2 style={{ fontSize: "var(--font-size-h2)" }}>{user?.display_name}</h2>
      <p style={{ color: "var(--color-text-secondary)" }}>
        TODO: Thesdel Score, rank, badge shelf (~17 families), season
        progress, contribution graph, partner streaks (§7.1-7.3).
      </p>
      <button type="button" onClick={() => void logout()}>
        Log out
      </button>
    </div>
  );
}
