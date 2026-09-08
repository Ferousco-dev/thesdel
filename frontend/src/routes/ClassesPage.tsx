import { useEffect, useState } from "react";
import { listMyClasses, createClass, joinClass } from "../lib/api/endpoints";
import type { ClassPublicWithRole } from "../lib/api/types";
import { isApiError } from "../lib/api/errors";
import { AnnouncementFeed } from "../components/AnnouncementFeed";

export function ClassesPage() {
  const [classes, setClasses] = useState<ClassPublicWithRole[] | null>(null);
  const [selectedClassId, setSelectedClassId] = useState<string | null>(null);
  const [joinCode, setJoinCode] = useState("");
  const [className, setClassName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [view, setView] = useState<"list" | "create" | "join">("list");

  const fetchClasses = () => {
    listMyClasses().then(setClasses).catch(err => setError(isApiError(err) ? err.message : "Failed to load classes"));
  };

  useEffect(() => {
    fetchClasses();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createClass(className);
      setClassName("");
      setView("list");
      fetchClasses();
    } catch (err) {
      alert(isApiError(err) ? err.message : "Create failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleJoin(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await joinClass(joinCode);
      setJoinCode("");
      setView("list");
      fetchClasses();
    } catch (err) {
      alert(isApiError(err) ? err.message : "Join failed");
    } finally {
      setSubmitting(false);
    }
  }

  const selectedClass = classes?.find(c => c.id === selectedClassId);

  if (classes === null) return <div style={{ padding: "3rem" }}>Loading…</div>;

  if (selectedClass) {
    return (
      <div style={{ padding: "2rem 3rem", height: "100%", display: "flex", flexDirection: "column" }}>
        <button type="button" className="btn btn--text" onClick={() => setSelectedClassId(null)} style={{ alignSelf: "flex-start", marginBottom: "1.5rem" }}>
          ← Back to classes
        </button>
        <h1 style={{ fontSize: "var(--font-size-h1)", marginBottom: "0.5rem" }}>{selectedClass.name}</h1>
        <div style={{ fontSize: "var(--font-size-caption)", color: "var(--color-text-secondary)", marginBottom: "2rem" }}>
          Join Code: <span className="tabular-nums" style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>{selectedClass.join_code}</span>
          {" · "}
          Role: <span style={{ textTransform: "capitalize" }}>{selectedClass.role}</span>
        </div>

        <AnnouncementFeed classId={selectedClass.id} userRole={selectedClass.role} />
      </div>
    );
  }

  return (
    <div style={{ padding: "2rem 3rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "2rem" }}>
        <div>
          <h1 style={{ fontSize: "var(--font-size-h1)", margin: 0, marginBottom: "0.5rem" }}>Classes</h1>
          <p style={{ color: "var(--color-text-secondary)", margin: 0, fontSize: "14px" }}>
            Join or create classes to collaborate with classmates
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button type="button" className="btn btn--ghost" onClick={() => setView("join")}>Join</button>
          <button type="button" className="btn btn--primary" onClick={() => setView("create")}>+ New</button>
        </div>
      </div>

      {error && <p className="auth-error">{error}</p>}

      {view === "create" && (
        <form onSubmit={handleCreate} style={{ marginBottom: "2rem", padding: "1.5rem", border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg)" }}>
          <h2 style={{ fontSize: "var(--font-size-h2)", marginBottom: "1rem" }}>Create a Class</h2>
          <div className="auth-field">
            <label htmlFor="className">Class Name</label>
            <input id="className" value={className} onChange={e => setClassName(e.target.value)} required placeholder="e.g. Physics 101" />
          </div>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
            <button type="submit" className="btn btn--primary" disabled={submitting}>Create</button>
            <button type="button" className="btn btn--ghost" onClick={() => setView("list")}>Cancel</button>
          </div>
        </form>
      )}

      {view === "join" && (
        <form onSubmit={handleJoin} style={{ marginBottom: "2rem", padding: "1.5rem", border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg)" }}>
          <h2 style={{ fontSize: "var(--font-size-h2)", marginBottom: "1rem" }}>Join a Class</h2>
          <div className="auth-field">
            <label htmlFor="joinCode">Join Code</label>
            <input id="joinCode" value={joinCode} onChange={e => setJoinCode(e.target.value)} required placeholder="7-character code" />
          </div>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
            <button type="submit" className="btn btn--primary" disabled={submitting}>Join</button>
            <button type="button" className="btn btn--ghost" onClick={() => setView("list")}>Cancel</button>
          </div>
        </form>
      )}

      <div style={{ display: "grid", gap: "1rem" }}>
        {classes.length === 0 ? (
          <div style={{ padding: "6rem 3rem", textAlign: "center", border: "2px dashed var(--color-border)", borderRadius: "var(--radius-lg)", backgroundColor: "var(--color-bg)" }}>
            <div style={{ fontSize: "48px", marginBottom: "1rem" }}>📚</div>
            <h2 style={{ fontSize: "20px", fontWeight: 600, marginBottom: "0.5rem" }}>No classes yet</h2>
            <p style={{ color: "var(--color-text-secondary)", marginBottom: "2rem", maxWidth: "400px", margin: "0 auto 2rem" }}>
              Create a new class or join an existing one using a join code to get started.
            </p>
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "center" }}>
              <button type="button" className="btn btn--ghost" onClick={() => setView("join")}>Join a class</button>
              <button type="button" className="btn btn--primary" onClick={() => setView("create")}>Create new</button>
            </div>
          </div>
        ) : (
          classes.map(c => (
            <button
              key={c.id}
              type="button"
              onClick={() => setSelectedClassId(c.id)}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                padding: "1rem 1.25rem",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              <span style={{ fontWeight: 600, fontSize: "var(--font-size-body)" }}>{c.name}</span>
              <span style={{ fontSize: "var(--font-size-caption)", color: "var(--color-text-secondary)" }}>
                {c.member_count} {c.member_count === 1 ? "member" : "members"}
              </span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
