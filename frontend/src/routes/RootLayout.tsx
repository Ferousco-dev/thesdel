import { Navigate, Outlet } from "react-router-dom";

import { Sidebar } from "../components/Sidebar";
import { NotificationCenter } from "../components/NotificationCenter";
import { useAuth } from "../lib/auth/useAuth";

export function RootLayout() {
  const { status, user } = useAuth();

  if (status === "loading") return null; // TODO: replace with a proper loading state
  if (status === "unauthenticated") return <Navigate to="/login" replace />;

  return (
    <div style={{ display: "flex", height: "100%", backgroundColor: "var(--color-bg)" }}>
      <Sidebar />
      <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
        <header
          style={{
            borderBottom: "1px solid var(--color-border)",
            padding: "1rem 1.5rem",
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            gap: "1rem",
            backgroundColor: "var(--color-surface)",
          }}
        >
          {user && <NotificationCenter userId={user.id} />}
        </header>
        <main style={{ flex: 1, overflowY: "auto" }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
