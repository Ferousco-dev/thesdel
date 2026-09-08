import { NavLink } from "react-router-dom";
import { useAuth } from "../lib/auth/useAuth";

const TABS = [
  { to: "/timetable", label: "Timetable", icon: "📅" },
  { to: "/classes", label: "Classes", icon: "📚" },
  { to: "/litheral", label: "Litheral", icon: "✨" },
  { to: "/profile", label: "Profile", icon: "👤" },
];

export function Sidebar() {
  const { user } = useAuth();

  return (
    <nav
      style={{
        width: "260px",
        backgroundColor: "var(--color-surface)",
        borderRight: "1px solid var(--color-border)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        boxShadow: "inset -1px 0 0 rgba(0,0,0,0.05)",
      }}
    >
      {/* Logo/Brand */}
      <div
        style={{
          padding: "1.5rem 1.25rem",
          borderBottom: "1px solid var(--color-border)",
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
        }}
      >
        <div
          style={{
            width: "40px",
            height: "40px",
            backgroundColor: "var(--color-primary)",
            borderRadius: "8px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: "bold",
            color: "white",
            fontSize: "20px",
          }}
        >
          🎓
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: "14px" }}>Thesdel</div>
          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {user?.tier || "free"}
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <div style={{ flex: 1, overflow: "auto", padding: "0.5rem" }}>
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            style={({ isActive }) => ({
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              padding: "0.75rem 1rem",
              marginBottom: "0.25rem",
              borderRadius: "8px",
              textDecoration: "none",
              color: isActive ? "white" : "var(--color-text)",
              backgroundColor: isActive ? "var(--color-primary)" : "transparent",
              cursor: "pointer",
              transition: "all 0.15s cubic-bezier(0.16, 1, 0.3, 1)",
              fontSize: "14px",
              fontWeight: isActive ? "600" : "500",
            })}
            onMouseEnter={(e) => {
              if (!e.currentTarget.style.backgroundColor.includes("var(--color-primary)")) {
                e.currentTarget.style.backgroundColor = "rgba(232, 89, 12, 0.08)";
              }
            }}
            onMouseLeave={(e) => {
              if (!e.currentTarget.style.backgroundColor.includes("var(--color-primary)")) {
                e.currentTarget.style.backgroundColor = "transparent";
              }
            }}
          >
            <span style={{ fontSize: "18px" }}>{tab.icon}</span>
            <span>{tab.label}</span>
          </NavLink>
        ))}
      </div>

      {/* User Info / Settings Footer */}
      <div
        style={{
          borderTop: "1px solid var(--color-border)",
          padding: "1rem 1.25rem",
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          fontSize: "13px",
        }}
      >
        <div
          style={{
            width: "32px",
            height: "32px",
            backgroundColor: "var(--color-primary)",
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
            fontWeight: "600",
            flexShrink: 0,
          }}
        >
          {user?.display_name?.[0]?.toUpperCase() || "?"}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontWeight: 500,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {user?.display_name}
          </div>
          <div style={{ color: "var(--color-text-secondary)", fontSize: "12px" }}>
            {user?.email}
          </div>
        </div>
      </div>
    </nav>
  );
}
