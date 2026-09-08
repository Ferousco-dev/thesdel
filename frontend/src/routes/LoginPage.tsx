import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";

import heroStudent1 from "../assets/hero-student-1.png";
import { GoogleSignInButton } from "../components/GoogleSignInButton";
import { isApiError } from "../lib/api/errors";
import { useAuth } from "../lib/auth/useAuth";
import "../styles/auth.css";

// Split-screen auth: branded panel (left, desktop only) + form (right).
// Same visual system as the landing page (orange/black, the flower-face
// logomark) but built with the app's own theme.css tokens rather than
// Tailwind — this screen is part of the authenticated app shell, not the
// marketing site.
export function LoginPage() {
  const { login, status } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === "authenticated") return <Navigate to="/timetable" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(isApiError(err) ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-screen">
      <aside className="auth-panel">
        <div className="auth-panel__brand">
          <svg width="28" height="28" viewBox="0 0 40 40" fill="none" aria-hidden="true">
            <defs>
              <linearGradient id="authLogoGradient" x1="5" y1="4" x2="35" y2="36" gradientUnits="userSpaceOnUse">
                <stop stopColor="#E8590C" />
                <stop offset="1" stopColor="#FFB385" />
              </linearGradient>
            </defs>
            <path
              d="M9 17.5 6.5 14l4.8-.6L14 9l3 3.4 3-3.4 2.7 4.4 4.8.6-2.5 3.5v7.2c0 5.1-3.6 8.3-9 8.3s-9-3.2-9-8.3v-7.2Z"
              fill="url(#authLogoGradient)"
            />
            <circle cx="13.5" cy="21" r="2" fill="white" />
            <circle cx="26.5" cy="21" r="2" fill="white" />
            <path d="M15 27c2.8 1.5 7.2 1.5 10 0" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          Thesdel
        </div>

        <div className="auth-panel__copy">
          <h2>Your class timetable. Then Litheral builds your week around it.</h2>
          <p>
            Build or join a class timetable for free. Premium and Pro add Litheral to plan your
            study time and, on Pro, your whole week — without ever hiding a class you're supposed
            to be in.
          </p>
        </div>

        <img
          className="auth-panel__figure"
          src={heroStudent1}
          alt=""
          aria-hidden="true"
          loading="lazy"
        />
      </aside>

      <div className="auth-form-side">
        <form onSubmit={handleSubmit} className="auth-form">
          <Link to="/" className="auth-form__back">
            ← Back to home
          </Link>

          <h1>Welcome back</h1>
          <p className="auth-form__subtitle">
            Sign in to see your timetable.
          </p>

          <div className="auth-field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="auth-field">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <label htmlFor="password">Password</label>
              <Link to="/forgot-password" style={{ fontSize: "var(--font-size-caption)", color: "var(--color-accent-text)", textDecoration: "none" }}>
                Forgot?
              </Link>
            </div>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>

          {error && (
            <p role="alert" className="auth-error">
              {error}
            </p>
          )}

          <button type="submit" className="btn btn--primary auth-submit" disabled={submitting}>
            Log in
          </button>

          <div className="auth-switch">
            Need an account? <Link to="/register">Sign up</Link>
          </div>

          <div className="auth-divider">or</div>
          <GoogleSignInButton onError={setError} />
        </form>
      </div>
    </div>
  );
}
