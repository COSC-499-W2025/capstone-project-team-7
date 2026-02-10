"use client";

import { useState, useEffect } from "react";
import { api, consent as consentApi } from "@/lib/api";
import { clearStoredToken, getStoredToken, setStoredToken } from "@/lib/auth";
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

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const accessToken = getStoredToken();

    if (storedUser && accessToken) {
      try {
        const parsedUser = JSON.parse(storedUser) as User;
        setUser(parsedUser);
      } catch (error) {
        localStorage.removeItem("user");
        clearStoredToken();
        localStorage.removeItem("refresh_token");
      }
    }

    setIsLoading(false);
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
        localStorage.setItem("refresh_token", refresh_token);
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
        localStorage.setItem("refresh_token", refresh_token);
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
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");

    setUser(null);
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
