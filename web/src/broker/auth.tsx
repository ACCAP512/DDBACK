// Auth context for the Broker OS SPA (M3): holds the signed-in principal, drives login/logout, and
// guards routes. The JWT lives in localStorage (api.ts); on boot we validate it via /auth/me so a
// stale token logs out cleanly rather than half-rendering an authenticated shell.

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api, ApiError, getToken, setToken } from "./api";
import type { Me } from "./api";

interface AuthState {
  me: Me | null;
  booting: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  can: (permission: string) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [booting, setBooting] = useState(true);

  // Validate any persisted token on first load.
  useEffect(() => {
    let live = true;
    if (!getToken()) {
      setBooting(false);
      return;
    }
    api
      .me()
      .then((m) => live && setMe(m))
      .catch(() => {
        setToken(null);
        if (live) setMe(null);
      })
      .finally(() => live && setBooting(false));
    return () => {
      live = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password);
    setToken(res.access_token);
    try {
      setMe(await api.me());
    } catch (e) {
      setToken(null);
      setMe(null);
      throw e;
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setMe(null);
  }, []);

  const can = useCallback(
    (permission: string) => !!me && me.permissions.includes(permission),
    [me],
  );

  const value = useMemo<AuthState>(
    () => ({ me, booting, login, logout, can }),
    [me, booting, login, logout, can],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

/** Route guard: redirect to /login (remembering where we came from) unless signed in. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { me, booting } = useAuth();
  const location = useLocation();
  if (booting) return <div className="bk-boot">Loading…</div>;
  if (!me) return <Navigate to="/login" replace state={{ from: location }} />;
  return <>{children}</>;
}

/** True when an API error means "your session ended" — used to bounce to login. */
export function isAuthError(e: unknown): boolean {
  return e instanceof ApiError && e.status === 401;
}
