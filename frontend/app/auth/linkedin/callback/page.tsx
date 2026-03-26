"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import { getStoredToken } from "@/lib/auth";
import { linkedInCallback } from "@/lib/api/portfolio";

function CallbackContent() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [name, setName] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (!code || !state) {
      setStatus("error");
      setErrorMsg("Missing authorization code or state parameter.");
      return;
    }

    const token = getStoredToken();
    if (!token) {
      setStatus("error");
      setErrorMsg("Not authenticated. Please log in and try again.");
      return;
    }

    linkedInCallback(token, { code, state })
      .then((res) => {
        setStatus("success");
        setName(res.linkedin_name ?? "");
        setTimeout(() => {
          if (window.opener) {
            window.opener.postMessage({ type: "linkedin-connected" }, "*");
            window.close();
          }
        }, 1500);
      })
      .catch((err) => {
        setStatus("error");
        setErrorMsg(err instanceof Error ? err.message : "Connection failed");
      });
  }, [searchParams]);

  return (
    <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center shadow-lg">
      {status === "loading" && (
        <>
          <Loader2 size={32} className="mx-auto mb-4 animate-spin text-[#0A66C2]" />
          <p className="text-sm font-medium text-foreground">Connecting LinkedIn...</p>
        </>
      )}
      {status === "success" && (
        <>
          <CheckCircle2 size={32} className="mx-auto mb-4 text-emerald-500" />
          <p className="text-sm font-medium text-foreground">
            Connected as {name || "LinkedIn user"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">This window will close shortly.</p>
        </>
      )}
      {status === "error" && (
        <>
          <XCircle size={32} className="mx-auto mb-4 text-red-500" />
          <p className="text-sm font-medium text-foreground">Connection failed</p>
          <p className="mt-1 text-xs text-muted-foreground">{errorMsg}</p>
          <button
            onClick={() => window.close()}
            className="mt-4 rounded-lg bg-muted px-4 py-2 text-xs font-medium text-foreground hover:bg-muted/80"
          >
            Close
          </button>
        </>
      )}
    </div>
  );
}

export default function LinkedInCallbackPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Suspense
        fallback={
          <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center shadow-lg">
            <Loader2 size={32} className="mx-auto mb-4 animate-spin text-[#0A66C2]" />
            <p className="text-sm font-medium text-foreground">Connecting LinkedIn...</p>
          </div>
        }
      >
        <CallbackContent />
      </Suspense>
    </div>
  );
}
