import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { requestPasswordReset } from "../lib/api/endpoints";
import { isApiError } from "../lib/api/errors";
import "../styles/auth.css";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await requestPasswordReset(email);
      setSuccess(true);
    } catch (err) {
      setError(isApiError(err) ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-form-side" style={{ flex: 1 }}>
        <form onSubmit={handleSubmit} className="auth-form" style={{ maxWidth: "400px" }}>
          <Link to="/login" className="auth-form__back">
            ← Back to login
          </Link>

          <h1>Forgot password</h1>
          <p className="auth-form__subtitle">
            Enter your email and we'll send you a link to reset your password.
          </p>

          {success ? (
            <div className="auth-success">
              <p>Check your email for a reset link. It will expire in 30 minutes.</p>
            </div>
          ) : (
            <>
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

              {error && (
                <p role="alert" className="auth-error">
                  {error}
                </p>
              )}

              <button type="submit" className="btn btn--primary auth-submit" disabled={submitting}>
                Send reset link
              </button>
            </>
          )}
        </form>
      </div>
    </div>
  );
}
