import { useCallback, useEffect, useState, type ReactNode } from "react";

import {
  getMe,
  googleAuth,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
} from "../api/endpoints";
import { tokenStore } from "../api/tokenStore";
import type { UserPublic } from "../api/types";
import { AuthContext, type AuthContextValue } from "./context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [status, setStatus] = useState<AuthContextValue["status"]>("loading");

  useEffect(() => {
    if (!tokenStore.get()) {
      setStatus("unauthenticated");
      return;
    }
    getMe()
      .then((me) => {
        setUser(me);
        setStatus("authenticated");
      })
      .catch(() => {
        tokenStore.clear();
        setStatus("unauthenticated");
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await apiLogin({ email, password });
    tokenStore.set({ accessToken: result.access_token, refreshToken: result.refresh_token });
    setUser(result.user);
    setStatus("authenticated");
  }, []);

  const register = useCallback(async (email: string, password: string, displayName: string) => {
    const result = await apiRegister({ email, password, display_name: displayName });
    tokenStore.set({ accessToken: result.access_token, refreshToken: result.refresh_token });
    setUser(result.user);
    setStatus("authenticated");
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const result = await googleAuth(idToken);
    tokenStore.set({ accessToken: result.access_token, refreshToken: result.refresh_token });
    setUser(result.user);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    const tokens = tokenStore.get();
    if (tokens) {
      await apiLogout(tokens.refreshToken).catch(() => {
        // Best-effort — even if the server call fails, clear local state
        // so the user isn't stuck "logged in" on this device.
      });
    }
    tokenStore.clear();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext.Provider value={{ user, status, login, register, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
