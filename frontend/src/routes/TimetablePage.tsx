import { useEffect, useState, useMemo } from "react";

import {
  listMyTimetable,
  createMyTimetableEntry,
  updateMyTimetableEntry,
  deleteMyTimetableEntry,
  type TimetableEntryInput
} from "../lib/api/endpoints";
import type { TimetableEntryPublic } from "../lib/api/types";
import { TimetableEntryForm } from "../components/TimetableEntryForm";
import { isApiError } from "../lib/api/errors";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOURS = Array.from({ length: 15 }, (_, i) => i + 8); // 8:00 to 22:00

export function TimetablePage() {
  const [entries, setEntries] = useState<TimetableEntryPublic[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<TimetableEntryPublic | undefined>();
  const [submitting, setSubmitting] = useState(false);

  const fetchTimetable = () => {
    listMyTimetable()
      .then(setEntries)
      .catch((err) => setError(isApiError(err) ? err.message : "Failed to load timetable"));
  };

  useEffect(() => {
    fetchTimetable();
  }, []);

  const handleOpenAdd = () => {
    setEditingEntry(undefined);
    setIsFormOpen(true);
  };

  const handleOpenEdit = (entry: TimetableEntryPublic) => {
    setEditingEntry(entry);
    setIsFormOpen(true);
  };

  const handleCloseForm = () => {
    setIsFormOpen(false);
    setEditingEntry(undefined);
  };

  async function handleSubmit(data: TimetableEntryInput) {
    setSubmitting(true);
    try {
      if (editingEntry) {
        await updateMyTimetableEntry(editingEntry.id, data);
      } else {
        await createMyTimetableEntry(data);
      }
      handleCloseForm();
      fetchTimetable();
    } catch (err) {
      alert(isApiError(err) ? err.message : "Action failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!editingEntry) return;
    if (!confirm("Are you sure you want to delete this class?")) return;
    setSubmitting(true);
    try {
      await deleteMyTimetableEntry(editingEntry.id);
      handleCloseForm();
      fetchTimetable();
    } catch (err) {
      alert(isApiError(err) ? err.message : "Delete failed");
    } finally {
      setSubmitting(false);
    }
  }

  const gridEntries = useMemo(() => {
    if (!entries) return [];
    return entries.map((entry) => {
      const [startH, startM] = entry.start_time.split(":").map(Number);
      const [endH, endM] = entry.end_time.split(":").map(Number);

      const startTotal = startH * 60 + startM;
      const endTotal = endH * 60 + endM;

      const gridStart = ((startTotal - 8 * 60) / 60) + 2; // +2 because row 1 is headers
      const gridEnd = ((endTotal - 8 * 60) / 60) + 2;

      // Adjusted day index (Backend 0=Sun, 1=Mon... -> Grid column 1=Mon, 7=Sun)
      const gridCol = entry.day_of_week === 0 ? 7 : entry.day_of_week;

      return { ...entry, gridStart, gridEnd, gridCol };
    });
  }, [entries]);

  if (entries === null) return <div style={{ padding: "2rem" }}>Loading…</div>;

  return (
    <div style={{ padding: "1rem", height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h1 style={{ fontSize: "var(--font-size-h1)", margin: 0 }}>Timetable</h1>
        <button type="button" className="btn btn--primary" onClick={handleOpenAdd}>
          + Add Class
        </button>
      </div>

      {error && <p className="auth-error">{error}</p>}

      <div style={{ flex: 1, overflow: "auto", position: "relative" }}>
        {entries.length === 0 ? (
          <div style={{ padding: "4rem 2rem", textAlign: "center", border: "2px dashed var(--color-border)", borderRadius: "var(--radius-lg)" }}>
            <p style={{ color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>Your timetable is empty.</p>
            <button type="button" className="btn btn--ghost" onClick={handleOpenAdd}>Create your first class</button>
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "50px repeat(7, 1fr)",
              gridTemplateRows: "auto repeat(14, 60px)",
              minWidth: "800px",
              border: "1px solid var(--color-border)",
              background: "var(--color-bg)",
            }}
          >
            {/* Headers */}
            <div style={{ gridRow: 1, gridColumn: 1 }}></div>
            {DAY_LABELS.map((day, i) => (
              <div
                key={day}
                style={{
                  gridRow: 1,
                  gridColumn: i + 2,
                  textAlign: "center",
                  padding: "0.5rem",
                  fontWeight: 600,
                  borderBottom: "1px solid var(--color-border)",
                  borderLeft: "1px solid var(--color-border)",
                }}
              >
                {day}
              </div>
            ))}

            {/* Time labels and Grid lines */}
            {HOURS.slice(0, -1).map((hour, i) => (
              <div
                key={hour}
                style={{
                  gridRow: i + 2,
                  gridColumn: 1,
                  textAlign: "right",
                  paddingRight: "0.5rem",
                  fontSize: "var(--font-size-caption)",
                  color: "var(--color-text-secondary)",
                  transform: "translateY(-50%)",
                }}
              >
                {hour}:00
              </div>
            ))}

            {/* Vertical grid lines */}
            {Array.from({ length: 7 }).map((_, i) => (
              <div
                key={i}
                style={{
                  gridRow: "2 / span 14",
                  gridColumn: i + 2,
                  borderLeft: "1px solid var(--color-border)",
                  pointerEvents: "none",
                }}
              ></div>
            ))}

            {/* Horizontal grid lines */}
            {HOURS.slice(0, -1).map((_, i) => (
              <div
                key={i}
                style={{
                  gridRow: i + 2,
                  gridColumn: "2 / span 7",
                  borderTop: "1px solid var(--color-border)",
                  pointerEvents: "none",
                }}
              ></div>
            ))}

            {/* Entries */}
            {gridEntries.map((entry) => (
              <button
                key={entry.id}
                type="button"
                onClick={() => handleOpenEdit(entry)}
                style={{
                  gridColumn: entry.gridCol + 1,
                  gridRowStart: Math.floor(entry.gridStart),
                  gridRowEnd: Math.ceil(entry.gridEnd),
                  margin: "2px",
                  padding: "4px 8px",
                  background: "var(--color-primary)",
                  color: "white",
                  border: "none",
                  borderRadius: "var(--radius-block)",
                  fontSize: "var(--font-size-caption)",
                  textAlign: "left",
                  cursor: "pointer",
                  overflow: "hidden",
                  display: "flex",
                  flexDirection: "column",
                  zIndex: 1,
                }}
              >
                <span style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {entry.subject}
                </span>
                <span className="tabular-nums" style={{ opacity: 0.9 }}>
                  {entry.start_time}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Entry Modal */}
      {isFormOpen && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 100,
          padding: "1rem",
        }}>
          <div style={{
            background: "var(--color-bg)",
            padding: "1.5rem",
            borderRadius: "var(--radius-lg)",
            width: "100%",
            maxWidth: "400px",
            boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
          }}>
            <h2 style={{ fontSize: "var(--font-size-h2)", marginBottom: "1.5rem" }}>
              {editingEntry ? "Edit Class" : "Add New Class"}
            </h2>

            <TimetableEntryForm
              initialData={editingEntry}
              onSubmit={handleSubmit}
              onCancel={handleCloseForm}
              submitting={submitting}
            />

            {editingEntry && (
              <button
                type="button"
                className="btn btn--text"
                style={{ color: "var(--color-error)", marginTop: "1rem", width: "100%" }}
                onClick={handleDelete}
                disabled={submitting}
              >
                Delete this class
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
