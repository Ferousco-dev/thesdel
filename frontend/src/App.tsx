import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./lib/auth/AuthContext";
import { applyThemeMode } from "./lib/theme";
import { ClassesPage } from "./routes/ClassesPage";
import { LandingPage } from "./routes/LandingPage";
import { LitheralPage } from "./routes/LitheralPage";
import { LoginPage } from "./routes/LoginPage";
import { ProfilePage } from "./routes/ProfilePage";
import { RootLayout } from "./routes/RootLayout";
import { TimetablePage } from "./routes/TimetablePage";

export function App() {
  useEffect(() => {
    // Frontend Spec §6.4: light/dark is available to every tier, defaults
    // to the OS preference until a settings screen lets the user override
    // it. TODO: persist the user's explicit choice once that screen exists.
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyThemeMode(prefersDark ? "dark" : "light");
  }, []);

  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RootLayout />}>
          <Route path="/timetable" element={<TimetablePage />} />
          <Route path="/classes" element={<ClassesPage />} />
          <Route path="/litheral" element={<LitheralPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/timetable" replace />} />
      </Routes>
    </AuthProvider>
  );
}
