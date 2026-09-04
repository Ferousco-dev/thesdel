import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth/useAuth";
import {
  getMyProgression, listMyBadges, listBadgeCatalog,
  listMyStreaks, checkInStreak, acceptStreak
} from "../lib/api/endpoints";
import type {
  ProgressionMe, UserBadgePublic, BadgePublic, StreakPublic
} from "../lib/api/types";
import { isApiError } from "../lib/api/errors";

export function ProfilePage() {
  const { user, logout } = useAuth();
  const [progression, setProgression] = useState<ProgressionMe | null>(null);
  const [myBadges, setMyBadges] = useState<UserBadgePublic[]>([]);
  const [catalog, setCatalog] = useState<BadgePublic[]>([]);
  const [streaks, setStreaks] = useState<StreakPublic[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [p, mb, c, s] = await Promise.all([
        getMyProgression(),
        listMyBadges(),
        listBadgeCatalog(),
        listMyStreaks()
      ]);
      setProgression(p);
      setMyBadges(mb);
      setCatalog(c);
      setStreaks(s);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  async function handleCheckIn(partnerId: string) {
    try {
      await checkInStreak(partnerId);
      fetchData();
    } catch (err) {
      alert(isApiError(err) ? err.message : "Check-in failed");
    }
  }

  async function handleAccept(inviterId: string) {
    try {
      await acceptStreak(inviterId);
      fetchData();
    } catch (err) {
      alert(isApiError(err) ? err.message : "Accept failed");
    }
  }

  if (loading) return <div style={{ padding: "2rem" }}>Loading…</div>;

  return (
    <div style={{ padding: "1.5rem", display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* Header & Stats */}
      <section style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "var(--font-size-display)", margin: 0 }}>{user?.display_name}</h1>
          <p style={{ color: "var(--color-text-secondary)", textTransform: "uppercase", fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.05em", marginTop: "0.25rem" }}>
            {progression?.rank} · {user?.tier} tier
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "var(--font-size-display)", fontWeight: 800, color: "var(--color-primary)" }}>
            {progression?.thesdel_score}
          </div>
          <div style={{ fontSize: "var(--font-size-caption)", color: "var(--color-text-secondary)", fontWeight: 600 }}>THESDEL SCORE</div>
        </div>
      </section>

      {/* Badge Shelf */}
      <section>
        <h2 style={{ fontSize: "var(--font-size-h2)", marginBottom: "1rem" }}>Badges</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(60px, 1fr))", gap: "1rem" }}>
          {catalog.map(badge => {
            const owned = myBadges.find(b => b.family_id === badge.family_id);
            return (
              <div
                key={badge.family_id}
                title={badge.description}
                style={{
                  aspectRatio: "1",
                  borderRadius: "50%",
                  background: owned ? "var(--color-surface)" : "transparent",
                  border: `2px solid ${owned ? "var(--color-primary)" : "var(--color-border)"}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "1.5rem",
                  filter: owned ? "none" : "grayscale(1) opacity(0.3)",
                  cursor: "help"
                }}
              >
                {badge.icon_key || "🏅"}
              </div>
            );
          })}
        </div>
      </section>

      {/* Partner Streaks */}
      <section>
        <h2 style={{ fontSize: "var(--font-size-h2)", marginBottom: "1rem" }}>Partner Streaks</h2>
        <div style={{ display: "grid", gap: "0.75rem" }}>
          {streaks.length === 0 ? (
            <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-caption)" }}>No active streaks. Invite a classmate to start one!</p>
          ) : (
            streaks.map(s => {
              const isInviter = s.user_a === user?.id;
              const isPending = s.status === "pending";
              const partnerId = isInviter ? s.user_b : s.user_a;

              return (
                <div
                  key={s.id}
                  style={{
                    padding: "1rem",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    background: "var(--color-surface)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center"
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600 }}>{partnerId.slice(0, 8)}…</div>
                    <div style={{ fontSize: "var(--font-size-caption)", color: "var(--color-text-secondary)" }}>
                      {isPending ? "Waiting to start" : `${s.current_streak} day streak`}
                    </div>
                  </div>
                  {isPending ? (
                    !isInviter && (
                      <button type="button" className="btn btn--primary" style={{ minHeight: "32px", height: "32px", fontSize: "0.8rem" }} onClick={() => handleAccept(partnerId)}>
                        Accept
                      </button>
                    )
                  ) : (
                    <button type="button" className="btn btn--ghost" style={{ minHeight: "32px", height: "32px", fontSize: "0.8rem" }} onClick={() => handleCheckIn(partnerId)}>
                      Check-in
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* Activity Heatmap Placeholder */}
      <section>
        <h2 style={{ fontSize: "var(--font-size-h2)", marginBottom: "0.5rem" }}>Activity</h2>
        <div style={{ height: "100px", background: "var(--color-surface)", borderRadius: "var(--radius-md)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-text-secondary)", fontSize: "var(--font-size-caption)" }}>
          Activity Heatmap Placeholder (§7.2)
        </div>
      </section>

      <button type="button" className="btn btn--ghost" onClick={() => void logout()} style={{ marginTop: "1rem", borderColor: "var(--color-error)", color: "var(--color-error)" }}>
        Log out
      </button>
    </div>
  );
}
