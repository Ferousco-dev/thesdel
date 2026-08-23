import { NavLink } from "react-router-dom";

// Primary navigation per Frontend Spec §3. Order and set are fixed by the
// spec — don't add a 5th tab without checking with product first.
const TABS = [
  { to: "/timetable", label: "Timetable" },
  { to: "/classes", label: "Classes" },
  { to: "/litheral", label: "Litheral" },
  { to: "/profile", label: "Profile" },
];

export function BottomNav() {
  return (
    <nav
      style={{
        position: "sticky",
        bottom: 0,
        display: "flex",
        borderTop: "1px solid var(--color-border)",
        background: "var(--color-surface)",
      }}
    >
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          style={({ isActive }) => ({
            flex: 1,
            textAlign: "center",
            padding: "0.75rem 0",
            minHeight: "var(--tap-target-min)",
            color: isActive ? "var(--color-primary)" : "var(--color-text-secondary)",
            textDecoration: "none",
            fontSize: "var(--font-size-caption)",
          })}
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
