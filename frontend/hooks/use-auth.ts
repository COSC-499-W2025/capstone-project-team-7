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
