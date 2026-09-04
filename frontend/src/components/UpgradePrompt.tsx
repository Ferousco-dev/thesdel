import type { Tier } from "../lib/api/types";

interface Props {
  requiredTier: Tier;
}

export function UpgradePrompt({ requiredTier }: Props) {
  const isPro = requiredTier === "pro";

  return (
    <div
      style={{
        padding: "2rem",
        textAlign: "center",
        background: "var(--color-surface)",
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--color-border)",
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        maxWidth: "400px",
        margin: "2rem auto"
      }}
    >
      <div
        style={{
          display: "inline-flex",
          padding: "0.5rem 1rem",
          borderRadius: "100px",
          background: isPro ? "#7c3aed" : "var(--color-primary)",
          color: "white",
          fontSize: "0.75rem",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          marginBottom: "1.5rem"
        }}
      >
        {requiredTier} Required
      </div>

      <h2 style={{ fontSize: "var(--font-size-h2)", marginBottom: "1rem" }}>
        Unlock Litheral {isPro ? "Life" : "Study"}
      </h2>

      <ul style={{
        listStyle: "none",
        padding: 0,
        margin: "0 0 2rem 0",
        textAlign: "left",
        display: "grid",
        gap: "0.75rem",
        fontSize: "var(--font-size-caption)"
      }}>
        {isPro ? (
          <>
            <li>✅ <strong>Full Life Organizer:</strong> Your routines moved around your study time.</li>
            <li>✅ <strong>Conflict Detection:</strong> Automatic alerts when you're overbooked.</li>
            <li>✅ <strong>Custom Branding:</strong> Swap the app accent color.</li>
            <li>✅ Everything in Premium.</li>
          </>
        ) : (
          <>
            <li>✅ <strong>AI Study Plans:</strong> Generated around your class timetable.</li>
            <li>✅ <strong>Exam Urgency:</strong> Priority shifts as test dates approach.</li>
            <li>✅ <strong>Smart Regeneration:</strong> Tweak blocks with one tap.</li>
          </>
        )}
      </ul>

      <button type="button" className="btn btn--primary" style={{ width: "100%", background: isPro ? "#7c3aed" : "var(--color-primary-dark)" }}>
        Upgrade to {requiredTier === "premium" ? "Premium" : "Pro"}
      </button>

      <p style={{ marginTop: "1rem", fontSize: "0.7rem", color: "var(--color-text-secondary)" }}>
        Billing integration coming soon.
      </p>
    </div>
  );
}
