import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";

import heroStudent1 from "../assets/hero-student-1.png";
import { GoogleSignInButton } from "../components/GoogleSignInButton";
import { isApiError } from "../lib/api/errors";
import { useAuth } from "../lib/auth/useAuth";
import "../styles/auth.css";

export function RegisterPage() {
  const { register, status } = useAuth();
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
      await register(email, password, displayName);
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
            study time and, on Pro, your whole week.
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

          <h1>Create your account</h1>
          <p className="auth-form__subtitle">
            Free forever for your timetable and class updates.
          </p>

          <div className="auth-field">
            <label htmlFor="displayName">Display name</label>
            <input
              id="displayName"
              autoComplete="name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
          </div>

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
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
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
            Sign up
          </button>

          <div className="auth-switch">
            Have an account? <Link to="/login">Log in</Link>
          </div>

          <div className="auth-divider">or</div>
          <GoogleSignInButton onError={setError} />
        </form>
      </div>
    </div>
  );
}
