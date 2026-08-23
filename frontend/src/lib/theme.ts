// Theme mode (all tiers) and accent color (Pro-only) per Frontend Spec
// §6.4. A curated palette, not a full color picker — spec asks for 6-8
// preset options plus a reset-to-default.

export type ThemeMode = "light" | "dark";

export const ACCENT_PRESETS: { name: string; primary: string; primaryDark: string }[] = [
  { name: "Thesdel Orange (default)", primary: "#e8590c", primaryDark: "#b8460a" },
  { name: "Amber", primary: "#d97706", primaryDark: "#b45309" },
  { name: "Crimson", primary: "#dc2626", primaryDark: "#b91c1c" },
  { name: "Violet", primary: "#7c3aed", primaryDark: "#6025c0" },
  { name: "Teal", primary: "#0d9488", primaryDark: "#0b7c72" },
  { name: "Rose", primary: "#e11d48", primaryDark: "#be123c" },
  { name: "Sky", primary: "#0284c7", primaryDark: "#026aa3" },
  { name: "Emerald", primary: "#059669", primaryDark: "#047857" },
];

export function applyThemeMode(mode: ThemeMode): void {
  document.documentElement.setAttribute("data-theme", mode);
}

export function applyAccent(primary: string, primaryDark: string): void {
  document.documentElement.style.setProperty("--color-primary", primary);
  document.documentElement.style.setProperty("--color-primary-dark", primaryDark);
}

export function resetAccentToDefault(): void {
  const [defaultAccent] = ACCENT_PRESETS;
  if (defaultAccent) applyAccent(defaultAccent.primary, defaultAccent.primaryDark);
}
