"use client";

import { useState, useEffect } from "react";
import { toast } from "@/lib/notifications";
import { api, consent as consentApi } from "@/lib/api";
import {
  auth as authApi,
  clearStoredRefreshToken,
  clearStoredToken,
  getStoredRefreshToken,
  getStoredToken,
  logout as callBackendLogout,
  setStoredRefreshToken,
  setStoredToken,
} from "@/lib/auth";
import type { User, AuthSessionResponse, ApiResult } from "@/lib/api.types";

interface UseAuthReturn {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<ApiResult<AuthSessionResponse>>;
  signup: (
    email: string,
    password: string,
    consents: { privacy: boolean; external: boolean }
  ) => Promise<ApiResult<AuthSessionResponse>>;
  logout: () => void;
}

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Key used to prevent re-hydration immediately after explicit logout.
  // Without this, navigating to /auth/login after logout can trigger
  // hydrateAuthState() which may recover a still-valid server session
  // and redirect the user back to the dashboard.
  const LOGOUT_FLAG_KEY = "auth_logged_out";
  // Listen for auth:signout events — dispatched by API 401/403 handlers and logout()
  useEffect(() => {
    const handleSignout = (e: Event) => {
      setUser(null);
      const expired = (e as CustomEvent).detail?.expired;
      if (expired) {
        toast.error("Your session has expired. Please log in again.", {
          id: "auth-expired", // prevents duplicate toasts from concurrent 401s
          duration: 3000,
        });
      }
    };

    window.addEventListener("auth:signout", handleSignout);
    return () => window.removeEventListener("auth:signout", handleSignout);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const hydrateAuthState = async () => {
      // Skip re-hydration if user just logged out explicitly
      if (sessionStorage.getItem(LOGOUT_FLAG_KEY)) {
        if (!cancelled) {
          setIsLoading(false);
        }
        return;
      }

      const storedUser = localStorage.getItem("user");
      const accessToken = getStoredToken();
      const refreshToken = getStoredRefreshToken();

      if (storedUser && accessToken) {
        try {
          const parsedUser = JSON.parse(storedUser) as User;
          if (!cancelled) {
            setUser(parsedUser);
            setIsLoading(false);
          }
          return;
        } catch {
          localStorage.removeItem("user");
        }
      }

      if (accessToken || refreshToken) {
        const sessionResult = await authApi.getSession(accessToken ?? undefined);
        if (!cancelled && sessionResult.ok) {
          const recoveredUser: User = {
            id: sessionResult.data.user_id,
            email: sessionResult.data.email ?? sessionResult.data.user_id,
          };
          localStorage.setItem("user", JSON.stringify(recoveredUser));
          setUser(recoveredUser);
        }
      }

      if (!cancelled) {
        setIsLoading(false);
      }
    };

    void hydrateAuthState();

    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (
    email: string,
    password: string
  ): Promise<ApiResult<AuthSessionResponse>> => {
    setIsLoading(true);
    const result = await api.auth.login(email, password);

    if (result.ok) {
      const { user_id, email: userEmail, access_token, refresh_token } = result.data;

      // Clear logout flag on successful login
      sessionStorage.removeItem(LOGOUT_FLAG_KEY);

      setStoredToken(access_token);
      if (refresh_token) {
        setStoredRefreshToken(refresh_token);
      }

      const userData: User = { id: user_id, email: userEmail };
      localStorage.setItem("user", JSON.stringify(userData));
      setUser(userData);
    }

    setIsLoading(false);
    return result;
  };

  const signup = async (
    email: string,
    password: string,
    consents: { privacy: boolean; external: boolean }
  ): Promise<ApiResult<AuthSessionResponse>> => {
    setIsLoading(true);
    const result = await api.auth.signup(email, password);

    if (result.ok) {
      const { user_id, email: userEmail, access_token, refresh_token } = result.data;

      // Clear logout flag on successful signup
      sessionStorage.removeItem(LOGOUT_FLAG_KEY);

      setStoredToken(access_token);
      if (refresh_token) {
        setStoredRefreshToken(refresh_token);
      }

      await consentApi.set({
        data_access: consents.privacy,
        external_services: consents.external,
        notice_acknowledged_at: new Date().toISOString(),
      });

      const userData: User = { id: user_id, email: userEmail };
      localStorage.setItem("user", JSON.stringify(userData));
      setUser(userData);
    }

    setIsLoading(false);
    return result;
  };

  const logout = (): void => {
    // Call backend to invalidate refresh token (fire-and-forget)
    callBackendLogout();

    // Set flag to prevent hydrateAuthState from recovering the session
    // after redirect to login page. Uses sessionStorage so it persists
    // across page navigations but clears when browser tab closes.
    sessionStorage.setItem(LOGOUT_FLAG_KEY, "1");

    // Clear all possible auth token keys (comprehensive cleanup from main)
    localStorage.removeItem("access_token");
    localStorage.removeItem("auth_access_token");
    clearStoredToken();
    clearStoredRefreshToken();
    localStorage.removeItem("user");

    setUser(null);

    // Notify all other useAuth instances (e.g. dashboard layout) to sync state
    window.dispatchEvent(new CustomEvent("auth:signout", { detail: { expired: false } }));
  };

  const isAuthenticated = user !== null;

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    signup,
    logout,
  };
}
