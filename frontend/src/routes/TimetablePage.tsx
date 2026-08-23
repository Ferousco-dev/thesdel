import { useEffect, useState } from "react";

import { listMyTimetable } from "../lib/api/endpoints";
import type { TimetableEntryPublic } from "../lib/api/types";

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

// Placeholder: day-view list per Frontend Spec §4.4. The real UI needs the
// week-grid view, current-time indicator, and detail sheet — this proves
// the data flow (fetch -> render) that those build on.
export function TimetablePage() {
  const [entries, setEntries] = useState<TimetableEntryPublic[] | null>(null);

  useEffect(() => {
    listMyTimetable().then(setEntries);
  }, []);

  if (entries === null) return <p>Loading…</p>;

  if (entries.length === 0) {
    // Empty state per Frontend Spec §9 — never a blank grid.
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <p>No classes yet.</p>
        <button type="button">Create your first class</button>
        <button type="button">Join a class</button>
      </div>
    );
  }

  return (
    <ul style={{ listStyle: "none", padding: "1rem", margin: 0 }}>
      {entries.map((entry) => (
        <li
          key={entry.id}
          style={{
            padding: "0.75rem 1rem",
            marginBottom: "0.5rem",
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface)",
          }}
        >
          <strong>{entry.subject}</strong>
          <div className="tabular-nums" style={{ color: "var(--color-text-secondary)" }}>
            {DAY_LABELS[entry.day_of_week]} · {entry.start_time}–{entry.end_time}
            {entry.location ? ` · ${entry.location}` : ""}
          </div>
        </li>
      ))}
    </ul>
  );
}
