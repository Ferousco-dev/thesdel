import { useEffect, useState } from "react";
import { listAnnouncements, postAnnouncement, updateAnnouncement } from "../lib/api/endpoints";
import type { AnnouncementPublic } from "../lib/api/types";
import { isApiError } from "../lib/api/errors";

interface Props {
  classId: string;
  userRole?: string;
}

export function AnnouncementFeed({ classId, userRole }: Props) {
  const [announcements, setAnnouncements] = useState<AnnouncementPublic[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [posting, setPosting] = useState(false);

  const isRep = userRole === "rep";

  const fetchAnnouncements = async (nextCursor?: string) => {
    setLoading(true);
    try {
      const page = await listAnnouncements(classId, nextCursor);
      if (nextCursor) {
        setAnnouncements(prev => [...prev, ...page.items]);
      } else {
        setAnnouncements(page.items);
      }
      setCursor(page.next_cursor);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnnouncements();
  }, [classId]);

  async function handlePost(e: React.FormEvent) {
    e.preventDefault();
    if (!newContent.trim()) return;
    setPosting(true);
    try {
      const posted = await postAnnouncement(classId, newContent);
      setAnnouncements(prev => [posted, ...prev]);
      setNewContent("");
    } catch (err) {
      alert(isApiError(err) ? err.message : "Post failed");
    } finally {
      setPosting(false);
    }
  }

  async function handleTogglePin(announcement: AnnouncementPublic) {
    try {
      const updated = await updateAnnouncement(classId, announcement.id, { pinned: !announcement.pinned });
      setAnnouncements(prev => prev.map(a => a.id === updated.id ? updated : a));
    } catch (err) {
      alert(isApiError(err) ? err.message : "Update failed");
    }
  }

  return (
    <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column", gap: "1rem" }}>
      {isRep && (
        <form onSubmit={handlePost} style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
          <input
            value={newContent}
            onChange={e => setNewContent(e.target.value)}
            placeholder="Post an announcement…"
            style={{ flex: 1, padding: "0.5rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", background: "var(--color-surface)", color: "var(--color-text-primary)" }}
          />
          <button type="submit" className="btn btn--primary" disabled={posting || !newContent.trim()}>Post</button>
        </form>
      )}

      {announcements.length === 0 && !loading && (
        <p style={{ color: "var(--color-text-secondary)", textAlign: "center", padding: "2rem" }}>No announcements yet.</p>
      )}

      {announcements.map(a => (
        <div
          key={a.id}
          style={{
            padding: "1rem",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            background: a.pinned ? "rgba(232, 89, 12, 0.05)" : "var(--color-surface)",
            borderColor: a.pinned ? "var(--color-primary)" : "var(--color-border)",
            position: "relative"
          }}
        >
          {a.pinned && (
            <div style={{ position: "absolute", top: "0.5rem", right: "0.5rem", fontSize: "0.7rem", color: "var(--color-primary)", fontWeight: 600 }}>
              PINNED
            </div>
          )}
          <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{a.content}</p>
          <div style={{ marginTop: "0.5rem", fontSize: "var(--font-size-caption)", color: "var(--color-text-secondary)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>{new Date(a.created_at).toLocaleDateString()}</span>
            {isRep && (
              <button type="button" className="btn btn--text" style={{ fontSize: "0.75rem" }} onClick={() => handleTogglePin(a)}>
                {a.pinned ? "Unpin" : "Pin"}
              </button>
            )}
          </div>
        </div>
      ))}

      {cursor && (
        <button type="button" className="btn btn--ghost" onClick={() => fetchAnnouncements(cursor)} disabled={loading} style={{ margin: "1rem 0" }}>
          {loading ? "Loading…" : "Load More"}
        </button>
      )}
    </div>
  );
}
