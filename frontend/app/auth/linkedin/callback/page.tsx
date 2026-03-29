"use client";

/**
 * Fallback LinkedIn OAuth callback page.
 *
 * In normal operation LinkedIn redirects to the *backend* GET endpoint
 * (`/api/linkedin/oauth/callback`) which handles token exchange directly.
 * This frontend page only exists as a safety net — it shows a simple
 * message telling the user to return to the app.
 */
export default function LinkedInCallbackPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center shadow-lg">
        <p className="text-sm font-medium text-foreground">
          LinkedIn authorization complete.
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          You can close this window and return to the app.
        </p>
      </div>
    </div>
  );
}
