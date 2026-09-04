import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { confirmPasswordReset } from "../lib/api/endpoints";
import { isApiError } from "../lib/api/errors";
import "../styles/auth.css";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await confirmPasswordReset({ token, new_password: password });
      setSuccess(true);
    } catch (err) {
      setError(isApiError(err) ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <div className="auth-screen">
        <div className="auth-form-side" style={{ flex: 1 }}>
          <div className="auth-form" style={{ maxWidth: "400px" }}>
            <h1>Invalid link</h1>
            <p>This password reset link is invalid or has expired.</p>
            <Link to="/forgot-password" style={{ color: "var(--color-accent-text)" }}>
              Request a new one
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-screen">
      <div className="auth-form-side" style={{ flex: 1 }}>
        <form onSubmit={handleSubmit} className="auth-form" style={{ maxWidth: "400px" }}>
          <h1>Set new password</h1>
          <p className="auth-form__subtitle">Choose a strong password for your account.</p>

          {success ? (
            <div className="auth-success">
              <p>Your password has been reset successfully.</p>
              <Link to="/login" className="btn btn--primary" style={{ display: "flex", textDecoration: "none" }}>
                Log in
              </Link>
            </div>
          ) : (
            <>
              <div className="auth-field">
                <label htmlFor="password">New Password</label>
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

              <div className="auth-field">
                <label htmlFor="confirmPassword">Confirm New Password</label>
                <input
                  id="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
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
                Reset password
              </button>
            </>
          )}
        </form>
      </div>
    </div>
  );
}
