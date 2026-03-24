"use client";

import { useCallback, useEffect, useState } from "react";
import { consent as consentApi, secrets as secretsApi } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";

export interface AiEligibilityState {
  externalConsent: boolean | null;
  apiKeyValid: boolean | null;
  eligibilityChecked: boolean;
  eligibilityLoading: boolean;
  eligibilityMessage: string | null;
  aiReady: boolean;
  checkEligibility: () => Promise<boolean>;
}

export function useAiEligibility(): AiEligibilityState {
  const [externalConsent, setExternalConsent] = useState<boolean | null>(null);
  const [apiKeyValid, setApiKeyValid] = useState<boolean | null>(null);
  const [eligibilityChecked, setEligibilityChecked] = useState(false);
  const [eligibilityLoading, setEligibilityLoading] = useState(false);
  const [eligibilityMessage, setEligibilityMessage] = useState<string | null>(null);
  const aiReady = externalConsent === true && apiKeyValid === true;

  const checkEligibility = useCallback(async (): Promise<boolean> => {
    const token = getStoredToken();
    if (!token) {
      setExternalConsent(false);
      setApiKeyValid(false);
      setEligibilityMessage("You are not logged in. Sign in from Settings.");
      setEligibilityChecked(true);
      return false;
    }
    setEligibilityLoading(true);
    setEligibilityMessage(null);
    try {
      const consentRes = await consentApi.get();
      if (!consentRes.ok) {
        setExternalConsent(false);
        setApiKeyValid(false);
        setEligibilityMessage(
          consentRes.status === 401 || consentRes.status === 403
            ? "Session expired. Log in again from Settings."
            : consentRes.error ?? "Unable to check consent status."
        );
        return false;
      }
      const hasConsent = Boolean(consentRes.data.external_services);
      setExternalConsent(hasConsent);
      if (!hasConsent) {
        setApiKeyValid(false);
        setEligibilityMessage(
          "External Data consent is not enabled. Enable it in Settings > Consent."
        );
        return false;
      }

      const verifyRes = await secretsApi.verify();
      if (!verifyRes.ok) {
        setApiKeyValid(false);
        setEligibilityMessage(
          "Your OpenAI API key is missing or invalid. Verify it in Settings."
        );
        return false;
      }
      if (!verifyRes.data.valid) {
        setApiKeyValid(false);
        setEligibilityMessage(
          verifyRes.data.message ??
            "Your OpenAI API key is missing or invalid. Verify it in Settings."
        );
        return false;
      }
      setApiKeyValid(true);
      setEligibilityMessage(null);
      return true;
    } catch (err) {
      setExternalConsent(false);
      setApiKeyValid(false);
      setEligibilityMessage(
        err instanceof Error ? err.message : "Failed to check AI requirements."
      );
      return false;
    } finally {
      setEligibilityLoading(false);
      setEligibilityChecked(true);
    }
  }, []);

  useEffect(() => {
    void checkEligibility();
  }, [checkEligibility]);

  return {
    externalConsent,
    apiKeyValid,
    eligibilityChecked,
    eligibilityLoading,
    eligibilityMessage,
    aiReady,
    checkEligibility,
  };
}
