"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { consent as consentApi } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";
import type { ConsentNotice, ConsentStatus } from "@/lib/api.types";

type NoticeState = {
  dataAccess: ConsentNotice | null;
  externalServices: ConsentNotice | null;
};

const EMPTY_NOTICES: NoticeState = {
  dataAccess: null,
  externalServices: null,
};

export default function ConsentManagementPage() {
  const [status, setStatus] = useState<ConsentStatus | null>(null);
  const [notices, setNotices] = useState<NoticeState>(EMPTY_NOTICES);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = getStoredToken();
    setIsAuthenticated(Boolean(token));
    setAuthChecked(true);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (!authChecked) {
        return;
      }

      if (!isAuthenticated) {
        if (!cancelled) {
          setError("You must be logged in to manage consent settings.");
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const [statusRes, dataNoticeRes, externalNoticeRes] = await Promise.all([
          consentApi.get(),
          consentApi.notice("file_analysis"),
          consentApi.notice("external_services"),
        ]);

        if (cancelled) {
          return;
        }

        if (!statusRes.ok) {
          if (statusRes.status === 401 || statusRes.status === 403) {
            setIsAuthenticated(false);
            setError("Your session expired. Please log in again to manage consent settings.");
            setLoading(false);
            return;
          }
          setError(statusRes.error || "Failed to load consent status.");
        } else {
          setStatus(statusRes.data);
        }

        setNotices({
          dataAccess: dataNoticeRes.ok ? dataNoticeRes.data : null,
          externalServices: externalNoticeRes.ok ? externalNoticeRes.data : null,
        });
      } catch (err) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : "Failed to load consent settings.";
          setError(msg);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [authChecked, isAuthenticated]);

  const updatedAtLabel = status?.updated_at
    ? new Date(status.updated_at).toLocaleString()
    : "Not available";

  const dataAccessUpdatedAtLabel = status?.data_access_updated_at
    ? new Date(status.data_access_updated_at).toLocaleString()
    : "Not available";

  const externalUpdatedAtLabel = status?.external_services_updated_at
    ? new Date(status.external_services_updated_at).toLocaleString()
    : "Not available";

  const updateConsent = async (
    dataAccess: boolean,
    externalServices: boolean,
    successMessage: string
  ) => {
    if (externalServices && !dataAccess) {
      setError("External services consent requires data access consent.");
      return;
    }

    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      const res = await consentApi.set({
        data_access: dataAccess,
        external_services: externalServices,
        notice_acknowledged_at: new Date().toISOString(),
      });

      if (!res.ok) {
        setError(res.error || "Failed to update consent preferences.");
        return;
      }

      setStatus(res.data);
      setMessage(successMessage);
      setTimeout(() => setMessage(null), 2500);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to update consent preferences.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDataAccessToggle = async (next: boolean) => {
    const nextExternal = next ? Boolean(status?.external_services) : false;
    await updateConsent(
      next,
      nextExternal,
      next
        ? "Data access consent enabled."
        : "Data access consent withdrawn. External services disabled."
    );
  };

  const handleExternalToggle = async (next: boolean) => {
    if (!status?.data_access && next) {
      setError("Enable data access first before enabling external services.");
      return;
    }

    await updateConsent(
      Boolean(status?.data_access),
      next,
      next ? "External services consent enabled." : "External services consent withdrawn."
    );
  };

  const revokeDataAccess = async () => {
    await updateConsent(false, false, "Data access consent withdrawn.");
  };

  const revokeExternalServices = async () => {
    await updateConsent(Boolean(status?.data_access), false, "External services consent withdrawn.");
  };

  const revokeAll = async () => {
    await updateConsent(false, false, "All consent settings withdrawn.");
  };

  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 mb-6">
        <Link href="/settings" className="text-sm text-gray-600 hover:text-gray-900 mb-2 inline-block">
          ← Back to settings
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Consent Management</h1>
        <p className="text-gray-600 mt-2">
          Review and update consent for data storage and external AI services.
        </p>
        <p className="text-xs text-gray-500 mt-3">Last updated: {updatedAtLabel}</p>
      </div>

      {authChecked && !isAuthenticated && (
        <Card className="bg-white border border-gray-200">
          <CardHeader>
            <CardTitle className="text-gray-900">Authentication Required</CardTitle>
            <CardDescription>Please log in from Settings before managing consent.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/settings">
              <Button className="bg-gray-900 text-white hover:bg-gray-800">Go to settings</Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {isAuthenticated && loading && (
        <Card className="bg-white border border-gray-200">
          <CardContent className="p-6 text-sm text-gray-600">Loading consent preferences...</CardContent>
        </Card>
      )}

      {isAuthenticated && !loading && (
        <div className="space-y-6">
          {error && (
            <Card className="bg-red-50 border border-red-200">
              <CardContent className="p-4 text-sm text-red-700">{error}</CardContent>
            </Card>
          )}

          {message && (
            <Card className="bg-green-50 border border-green-200">
              <CardContent className="p-4 text-sm text-green-700">{message}</CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="bg-white border border-gray-200">
              <CardHeader>
                <CardTitle className="text-gray-900">Data Access Consent</CardTitle>
                <CardDescription>
                  Allows file analysis and metadata storage for your account.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm font-medium text-gray-900">Data analysis and storage</Label>
                    <p className="text-xs text-gray-500 mt-1">
                      Required for project scanning, history, and persistence.
                    </p>
                  </div>
                  <Switch
                    checked={Boolean(status?.data_access)}
                    onCheckedChange={handleDataAccessToggle}
                    disabled={saving}
                  />
                </div>

                <div className="flex items-center justify-between border-t border-gray-200 pt-3">
                  <div>
                    <span className="text-sm text-gray-700 block">
                      {status?.data_access ? "Granted" : "Not granted"}
                    </span>
                    <span className="text-xs text-gray-500 block mt-1">Updated: {dataAccessUpdatedAtLabel}</span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={revokeDataAccess}
                    disabled={saving || !status?.data_access}
                    className="border-red-300 text-red-600 hover:bg-red-50"
                  >
                    Withdraw
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white border border-gray-200">
              <CardHeader>
                <CardTitle className="text-gray-900">External AI Services Consent</CardTitle>
                <CardDescription>
                  Allows external AI/LLM providers for advanced analysis features.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm font-medium text-gray-900">External providers</Label>
                    <p className="text-xs text-gray-500 mt-1">
                      Requires data access consent to be enabled.
                    </p>
                  </div>
                  <Switch
                    checked={Boolean(status?.external_services)}
                    onCheckedChange={handleExternalToggle}
                    disabled={saving || !status?.data_access}
                  />
                </div>

                {!status?.data_access && (
                  <p className="text-xs text-amber-600">Enable data access first to grant external services consent.</p>
                )}

                <div className="flex items-center justify-between border-t border-gray-200 pt-3">
                  <div>
                    <span className="text-sm text-gray-700 block">
                      {status?.external_services ? "Granted" : "Not granted"}
                    </span>
                    <span className="text-xs text-gray-500 block mt-1">Updated: {externalUpdatedAtLabel}</span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={revokeExternalServices}
                    disabled={saving || !status?.external_services}
                    className="border-red-300 text-red-600 hover:bg-red-50"
                  >
                    Withdraw
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="bg-white border border-gray-200">
            <CardHeader>
              <CardTitle className="text-gray-900">Consent Notices</CardTitle>
              <CardDescription>
                Transparency details for each consent category.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[notices.dataAccess, notices.externalServices].filter(Boolean).map((notice) => (
                <div key={notice!.service} className="border border-gray-200 rounded-lg p-4">
                  <p className="text-sm font-semibold text-gray-900">{notice!.service}</p>
                  <p className="text-sm text-gray-600 mt-1">{notice!.privacy_notice}</p>
                  {notice!.implications.length > 0 && (
                    <ul className="list-disc pl-5 mt-2 text-xs text-gray-600 space-y-1">
                      {notice!.implications.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="bg-white border border-gray-200">
            <CardHeader>
              <CardTitle className="text-gray-900">Global Action</CardTitle>
              <CardDescription>
                Revoke both consent categories in one action.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                onClick={revokeAll}
                disabled={saving || (!status?.data_access && !status?.external_services)}
                className="border-red-300 text-red-600 hover:bg-red-50"
              >
                Revoke all consent
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
