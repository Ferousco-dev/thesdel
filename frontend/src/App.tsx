import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./lib/auth/AuthContext";
import { applyThemeMode } from "./lib/theme";
import { ClassesPage } from "./routes/ClassesPage";
import { LandingPage } from "./routes/LandingPage";
import { LitheralPage } from "./routes/LitheralPage";
import { LoginPage } from "./routes/LoginPage";
import { AboutPage } from "./routes/marketing/AboutPage";
import { ContactPage } from "./routes/marketing/ContactPage";
import { CookieSettingsPage } from "./routes/marketing/CookieSettingsPage";
import { PrivacyPolicyPage } from "./routes/marketing/PrivacyPolicyPage";
import { SupportPage } from "./routes/marketing/SupportPage";
import { TermsOfServicePage } from "./routes/marketing/TermsOfServicePage";
import { RegisterPage } from "./routes/RegisterPage";
import { ForgotPasswordPage } from "./routes/ForgotPasswordPage";
import { ResetPasswordPage } from "./routes/ResetPasswordPage";
import { VerifyEmailPage } from "./routes/VerifyEmailPage";
import { TimetableImportPage } from "./routes/TimetableImportPage";
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
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/support" element={<SupportPage />} />
        <Route path="/privacy" element={<PrivacyPolicyPage />} />
        <Route path="/terms" element={<TermsOfServicePage />} />
        <Route path="/cookies" element={<CookieSettingsPage />} />
        <Route element={<RootLayout />}>
          <Route path="/timetable" element={<TimetablePage />} />
          <Route path="/classes" element={<ClassesPage />} />
          <Route path="/litheral" element={<LitheralPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/onboarding/import" element={<TimetableImportPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/timetable" replace />} />
      </Routes>
    </AuthProvider>
  );
}
