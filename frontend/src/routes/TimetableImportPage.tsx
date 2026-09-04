import { useState, type ChangeEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { uploadTimetableImport } from "../lib/api/endpoints";
import { isApiError } from "../lib/api/errors";
import "../styles/auth.css";

export function TimetableImportPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  async function handleFileUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setSubmitting(true);
    try {
      await uploadTimetableImport(file);
      setUploadSuccess(true);
      // Backend only stores it for now, so we just tell the user and
      // move on. In a real flow, we'd wait for parsing.
    } catch (err) {
      setError(isApiError(err) ? err.message : "Upload failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "600px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "var(--font-size-display)", marginBottom: "1rem" }}>
        How do you want to start?
      </h1>
      <p style={{ color: "var(--color-text-secondary)", marginBottom: "2rem" }}>
        Thesdel works best when it knows your class schedule.
      </p>

      <div style={{ display: "grid", gap: "1.5rem" }}>
        <div
          style={{
            padding: "1.5rem",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-lg)",
            background: "var(--color-surface)",
          }}
        >
          <h2 style={{ fontSize: "var(--font-size-h2)", marginBottom: "0.5rem" }}>
            Import from Photo
          </h2>
          <p style={{ fontSize: "var(--font-size-caption)", color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>
            Take a photo of your printed timetable or upload a screenshot. We'll parse it for you.
          </p>

          {uploadSuccess ? (
            <div className="auth-success" style={{ marginBottom: 0 }}>
              <p>Timetable uploaded! We'll start parsing it shortly.</p>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => navigate("/timetable")}
              >
                Go to Timetable
              </button>
            </div>
          ) : (
            <>
              <input
                type="file"
                id="timetable-file"
                accept="image/jpeg,image/png,image/webp"
                style={{ display: "none" }}
                onChange={handleFileUpload}
                disabled={submitting}
              />
              <label
                htmlFor="timetable-file"
                className="btn btn--primary"
                style={{ cursor: "pointer", display: "inline-flex" }}
              >
                {submitting ? "Uploading…" : "Choose Photo"}
              </label>
            </>
          )}
          {error && <p className="auth-error" style={{ marginTop: "1rem" }}>{error}</p>}
        </div>

        <div
          style={{
            padding: "1.5rem",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <h2 style={{ fontSize: "var(--font-size-h2)", marginBottom: "0.5rem" }}>
            Manual Entry
          </h2>
          <p style={{ fontSize: "var(--font-size-caption)", color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>
            Prefer to type it in yourself? You can add your classes one by one.
          </p>
          <Link to="/timetable" className="btn btn--ghost" style={{ display: "inline-flex" }}>
            Start Manually
          </Link>
        </div>
      </div>
    </div>
  );
}
