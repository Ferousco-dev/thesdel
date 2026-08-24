import { useEffect, useRef } from "react";

import { isApiError } from "../lib/api/errors";
import { useAuth } from "../lib/auth/useAuth";

// Minimal local types for Google Identity Services — @types/google.accounts
// isn't installed, and the full SDK surface isn't needed for just "render
// a sign-in button and get a credential back."
interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleAccountsId {
  initialize: (config: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
  }) => void;
  renderButton: (
    parent: HTMLElement,
    options: { theme?: string; size?: string; width?: number },
  ) => void;
}

declare global {
  interface Window {
    google?: { accounts: { id: GoogleAccountsId } };
  }
}

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;
const GIS_SCRIPT_SRC = "https://accounts.google.com/gsi/client";

/** Renders Google's own "Sign in with Google" button (via Google Identity
 * Services' ID-token flow — see backend docs/DECISIONS.md ADR-011) and
 * wires its result into loginWithGoogle. Omits itself entirely if no
 * Client ID is configured, rather than rendering a button that can only
 * fail. */
export function GoogleSignInButton({ onError }: { onError: (message: string) => void }) {
  const { loginWithGoogle } = useAuth();
  const buttonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    let cancelled = false;

    function renderButton() {
      if (cancelled || !window.google || !buttonRef.current) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID as string,
        callback: (response) => {
          loginWithGoogle(response.credential).catch((err: unknown) => {
            onError(isApiError(err) ? err.message : "Google sign-in failed.");
          });
        },
      });
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "outline",
        size: "large",
        width: 320,
      });
    }

    if (window.google) {
      renderButton();
      return () => {
        cancelled = true;
      };
    }

    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GIS_SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", renderButton);
      return () => {
        cancelled = true;
        existing.removeEventListener("load", renderButton);
      };
    }

    const script = document.createElement("script");
    script.src = GIS_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = renderButton;
    document.head.appendChild(script);

    return () => {
      cancelled = true;
      // Script itself is left in place — removing it mid-load (e.g. a fast
      // remount) can leave window.google half-initialized for whichever
      // instance mounts next.
    };
  }, [loginWithGoogle, onError]);

  if (!GOOGLE_CLIENT_ID) return null;

  return <div ref={buttonRef} />;
}
