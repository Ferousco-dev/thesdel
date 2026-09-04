import { useState } from "react";
import type { SubjectInput } from "../lib/api/endpoints";

interface Props {
  subjects: string[];
  onSubmit: (subjects: SubjectInput[]) => Promise<void>;
  submitting?: boolean;
}

export function StudyPlanConfig({ subjects: initialSubjects, onSubmit, submitting }: Props) {
  const [configs, setConfigs] = useState<SubjectInput[]>(
    initialSubjects.map(s => ({ subject: s, priority: 3, exam_date: null }))
  );

  function updateConfig(index: number, patch: Partial<SubjectInput>) {
    setConfigs(prev => prev.map((c, i) => i === index ? { ...c, ...patch } : c));
  }

  return (
    <div style={{ display: "grid", gap: "1.5rem" }}>
      <div style={{ display: "grid", gap: "1rem" }}>
        {configs.map((config, i) => (
          <div
            key={config.subject}
            style={{
              padding: "1rem",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              background: "var(--color-surface)"
            }}
          >
            <h3 style={{ fontSize: "var(--font-size-h3)", marginBottom: "1rem" }}>{config.subject}</h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              <div className="auth-field">
                <label>Priority (1-5)</label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={config.priority || 3}
                  onChange={e => updateConfig(i, { priority: Number(e.target.value) })}
                />
              </div>
              <div className="auth-field">
                <label>Exam Date (Optional)</label>
                <input
                  type="date"
                  value={config.exam_date || ""}
                  onChange={e => updateConfig(i, { exam_date: e.target.value || null })}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      <button
        type="button"
        className="btn btn--primary"
        onClick={() => onSubmit(configs)}
        disabled={submitting}
        style={{ width: "100%" }}
      >
        {submitting ? "Generating Study Plan…" : "Generate Study Plan"}
      </button>
    </div>
  );
}
