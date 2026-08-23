import { Navigate, Outlet } from "react-router-dom";

import { BottomNav } from "../components/BottomNav";
import { useAuth } from "../lib/auth/useAuth";

export function RootLayout() {
  const { status } = useAuth();

  if (status === "loading") return null; // TODO: replace with a proper loading state
  if (status === "unauthenticated") return <Navigate to="/login" replace />;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <main style={{ flex: 1, overflowY: "auto" }}>
        <Outlet />
      </main>
      <BottomNav />
    </div>
  );
}
