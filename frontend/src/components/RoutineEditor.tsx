import { useState } from "react";
import { createRoutine, updateRoutine, deleteRoutine } from "../lib/api/endpoints";
import type { RoutinePublic } from "../lib/api/types";
import { isApiError } from "../lib/api/errors";

interface Props {
  routines: RoutinePublic[];
  onChanged: () => void;
}

const LABELS: RoutinePublic["label"][] = ["Sleep", "Work", "Gym", "Meals", "Church", "Personal"];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function RoutineEditor({ routines, onChanged }: Props) {
  const [editingId, setEditingId] = useState<string | "new" | null>(null);
  const [label, setLabel] = useState<RoutinePublic["label"]>("Personal");
  const [days, setDays] = useState<number[]>([]);
  const [startTime, setStartTime] = useState("08:00");
  const [endTime, setEndTime] = useState("09:00");
  const [isFlexible, setIsFlexible] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function startNew() {
    setEditingId("new");
    setLabel("Personal");
    setDays([1, 2, 3, 4, 5]);
    setStartTime("08:00");
    setEndTime("09:00");
    setIsFlexible(false);
  }

  function startEdit(r: RoutinePublic) {
    setEditingId(r.id);
    setLabel(r.label);
    setDays(r.days);
    setStartTime(r.start_time);
    setEndTime(r.end_time);
    setIsFlexible(r.is_flexible);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = { label, days, start_time: startTime, end_time: endTime, is_flexible: isFlexible };
      if (editingId === "new") {
        await createRoutine(payload);
      } else if (editingId) {
        await updateRoutine(editingId, payload);
      }
      setEditingId(null);
      onChanged();
    } catch (err) {
      alert(isApiError(err) ? err.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this routine?")) return;
    try {
      await deleteRoutine(id);
      onChanged();
    } catch (err) {
      alert(isApiError(err) ? err.message : "Delete failed");
    }
  }

  function toggleDay(day: number) {
    setDays(prev => prev.includes(day) ? prev.filter(d => d !== day) : [...prev, day]);
  }

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ fontSize: "var(--font-size-h3)", margin: 0 }}>My Routines</h3>
        <button type="button" className="btn btn--text" onClick={startNew}>+ Add Routine</button>
      </div>

      <div style={{ display: "grid", gap: "0.75rem" }}>
        {routines.map(r => (
          <div key={r.id} style={{ padding: "0.75rem", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 600 }}>{r.label}</div>
              <div style={{ fontSize: "var(--font-size-caption)", color: "var(--color-text-secondary)" }}>
                {r.start_time}–{r.end_time} · {r.days.map(d => DAYS[d]).join(", ")}
                {r.is_flexible && " · Flexible"}
              </div>
            </div>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button type="button" className="btn btn--text" onClick={() => startEdit(r)}>Edit</button>
              <button type="button" className="btn btn--text" style={{ color: "var(--color-error)" }} onClick={() => handleDelete(r.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>

      {editingId && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem" }}>
          <form onSubmit={handleSave} style={{ background: "var(--color-bg)", padding: "1.5rem", borderRadius: "var(--radius-lg)", width: "100%", maxWidth: "400px" }}>
            <h2 style={{ fontSize: "var(--font-size-h2)", marginBottom: "1.5rem" }}>{editingId === "new" ? "New Routine" : "Edit Routine"}</h2>

            <div className="auth-field">
              <label>What is this?</label>
              <select
                value={label}
                onChange={e => setLabel(e.target.value as any)}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", background: "var(--color-surface)", color: "var(--color-text-primary)" }}
              >
                {LABELS.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>

            <div className="auth-field" style={{ marginTop: "1rem" }}>
              <label>Which days?</label>
              <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap" }}>
                {[1,2,3,4,5,6,0].map(d => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => toggleDay(d)}
                    style={{
                      minWidth: "40px",
                      padding: "0.25rem",
                      fontSize: "0.75rem",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--color-border)",
                      background: days.includes(d) ? "var(--color-primary)" : "var(--color-surface)",
                      color: days.includes(d) ? "white" : "var(--color-text-primary)"
                    }}
                  >
                    {DAYS[d]}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "1rem" }}>
              <div className="auth-field">
                <label>Start</label>
                <input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} required />
              </div>
              <div className="auth-field">
                <label>End</label>
                <input type="time" value={endTime} onChange={e => setEndTime(e.target.value)} required />
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "1rem" }}>
              <input type="checkbox" id="flexible" checked={isFlexible} onChange={e => setIsFlexible(e.target.checked)} />
              <label htmlFor="flexible" style={{ fontSize: "var(--font-size-caption)" }}>This is flexible (can be moved if there's a conflict)</label>
            </div>

            <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.5rem" }}>
              <button type="submit" className="btn btn--primary" style={{ flex: 1 }} disabled={submitting}>Save</button>
              <button type="button" className="btn btn--ghost" style={{ flex: 1 }} onClick={() => setEditingId(null)} disabled={submitting}>Cancel</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
