import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { verifyEmail } from "../lib/api/endpoints";
import { isApiError } from "../lib/api/errors";
import "../styles/auth.css";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setError("Missing verification token.");
      return;
    }

    verifyEmail(token)
      .then(() => setStatus("success"))
      .catch((err) => {
        setStatus("error");
        setError(isApiError(err) ? err.message : "Something went wrong.");
      });
  }, [token]);

  return (
    <div className="auth-screen">
      <div className="auth-form-side" style={{ flex: 1 }}>
        <div className="auth-form" style={{ maxWidth: "400px" }}>
          {status === "verifying" && (
            <>
              <h1>Verifying email…</h1>
              <p>Please wait while we confirm your email address.</p>
            </>
          )}

          {status === "success" && (
            <>
              <h1>Email verified!</h1>
              <p>Your email has been successfully verified. You can now access all features.</p>
              <Link to="/timetable" className="btn btn--primary" style={{ display: "flex", textDecoration: "none" }}>
                Continue to app
              </Link>
            </>
          )}

          {status === "error" && (
            <>
              <h1>Verification failed</h1>
              <p role="alert" className="auth-error">
                {error || "This verification link is invalid or has expired."}
              </p>
              <Link to="/profile" style={{ color: "var(--color-accent-text)" }}>
                Go to profile
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
