import { useState, type FormEvent } from "react";
import type { TimetableEntryInput } from "../lib/api/endpoints";
import type { TimetableEntryPublic } from "../lib/api/types";

interface Props {
  initialData?: TimetableEntryPublic;
  onSubmit: (data: TimetableEntryInput) => Promise<void>;
  onCancel: () => void;
  submitting?: boolean;
}

const DAYS = [
  { value: 1, label: "Monday" },
  { value: 2, label: "Tuesday" },
  { value: 3, label: "Wednesday" },
  { value: 4, label: "Thursday" },
  { value: 5, label: "Friday" },
  { value: 6, label: "Saturday" },
  { value: 0, label: "Sunday" },
];

export function TimetableEntryForm({ initialData, onSubmit, onCancel, submitting }: Props) {
  const [subject, setSubject] = useState(initialData?.subject || "");
  const [dayOfWeek, setDayOfWeek] = useState(initialData?.day_of_week ?? 1);
  const [startTime, setStartTime] = useState(initialData?.start_time || "09:00");
  const [endTime, setEndTime] = useState(initialData?.end_time || "10:00");
  const [location, setLocation] = useState(initialData?.location || "");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await onSubmit({
      subject,
      day_of_week: dayOfWeek,
      start_time: startTime,
      end_time: endTime,
      location: location || null,
    });
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: "1rem" }}>
      <div className="auth-field">
        <label htmlFor="subject">Subject</label>
        <input
          id="subject"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          required
          placeholder="e.g. Mathematics"
        />
      </div>

      <div className="auth-field">
        <label htmlFor="day">Day</label>
        <select
          id="day"
          value={dayOfWeek}
          onChange={(e) => setDayOfWeek(Number(e.target.value))}
          style={{
            width: "100%",
            padding: "0.5rem",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            background: "var(--color-surface)",
            color: "var(--color-text-primary)",
          }}
        >
          {DAYS.map((d) => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div className="auth-field">
          <label htmlFor="start">Start Time</label>
          <input
            id="start"
            type="time"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            required
          />
        </div>
        <div className="auth-field">
          <label htmlFor="end">End Time</label>
          <input
            id="end"
            type="time"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            required
          />
        </div>
      </div>

      <div className="auth-field">
        <label htmlFor="location">Location (Optional)</label>
        <input
          id="location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="e.g. Room 402"
        />
      </div>

      <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
        <button
          type="submit"
          className="btn btn--primary"
          style={{ flex: 1 }}
          disabled={submitting}
        >
          {initialData ? "Save Changes" : "Add Class"}
        </button>
        <button
          type="button"
          className="btn btn--ghost"
          style={{ flex: 1 }}
          onClick={onCancel}
          disabled={submitting}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
