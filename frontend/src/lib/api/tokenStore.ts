// Scaffold decision, not a final one: tokens are kept in localStorage so a
// refresh survives a tab reload without extra backend work. A stolen XSS
// payload can read localStorage, so if/when this app handles genuinely
// sensitive flows (payment, etc.) reconsider moving the refresh token to
// an HttpOnly cookie set by a backend endpoint instead — that requires a
// backend change (the API currently returns refresh_token in the JSON
// body, see docs/API.md), so don't change this file alone without also
// changing app/auth/router.py. Flag this tradeoff to the user if asked to
// harden auth further; don't silently pick a different storage strategy.

const ACCESS_TOKEN_KEY = "thesdel.access_token";
const REFRESH_TOKEN_KEY = "thesdel.refresh_token";

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
}

export const tokenStore = {
  get(): TokenPair | null {
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!accessToken || !refreshToken) return null;
    return { accessToken, refreshToken };
  },
  set(tokens: TokenPair): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
  },
  clear(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};
