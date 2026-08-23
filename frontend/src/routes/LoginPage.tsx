import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";

import { isApiError } from "../lib/api/errors";
import { useAuth } from "../lib/auth/useAuth";

// Placeholder auth screen — covers the "Sign up / log in" step of
// Frontend Spec §4.1. The "Create a class" vs "Join a class" path choice
// that follows belongs on its own onboarding screen once a design exists;
// this page only proves the auth wiring works end to end.
export function LoginPage() {
  const { login, register, status } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === "authenticated") return <Navigate to="/timetable" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, displayName);
      }
    } catch (err) {
      setError(isApiError(err) ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ padding: "2rem", maxWidth: 360, margin: "0 auto" }}>
      <h1 style={{ fontSize: "var(--font-size-display)" }}>Thesdel</h1>

      {mode === "register" && (
        <input
          placeholder="Display name"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          required
        />
      )}
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        minLength={8}
      />

      {error && (
        <p role="alert" style={{ color: "var(--color-error)" }}>
          {error}
        </p>
      )}

      <button type="submit" disabled={submitting}>
        {mode === "login" ? "Log in" : "Sign up"}
      </button>

      <button type="button" onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "Need an account? Sign up" : "Have an account? Log in"}
      </button>
    </form>
  );
}
