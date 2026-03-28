"use client";

import { useEffect, useState, FormEvent, useMemo } from "react";
import type { ChangeEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { PasswordStrength } from "@/components/password-strength";

export default function SignupPage() {
  const router = useRouter();
  const { signup, isLoading, isAuthenticated } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [privacyConsent, setPrivacyConsent] = useState(false);
  const [externalConsent, setExternalConsent] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeNotice, setActiveNotice] = useState<"privacy" | "external" | null>(null);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/");
    }
  }, [isAuthenticated, isLoading, router]);

  const passwordValidation = useMemo(() => {
    const hasMinLength = password.length >= 8;
    const hasUppercase = /[A-Z]/.test(password);
    const hasLowercase = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);

    return {
      hasMinLength,
      hasUppercase,
      hasLowercase,
      hasNumber,
      isValid: hasMinLength && hasUppercase && hasLowercase && hasNumber,
    };
  }, [password]);

  const isEmailValid = useMemo(() => {
    const trimmed = email.trim();
    return trimmed.length > 0 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed);
  }, [email]);

  if (isLoading || isAuthenticated) {
    return (
      <main
        className="min-h-screen flex items-center justify-center p-4"
        role="status"
        aria-busy="true"
        aria-live="polite"
      >
        <p className="text-sm text-muted-foreground">Loading...</p>
      </main>
    );
  }

  const passwordsMatch = password === confirmPassword && confirmPassword.length > 0;

  const canSubmit =
    isEmailValid &&
    passwordValidation.isValid &&
    passwordsMatch &&
    privacyConsent &&
    !isSubmitting;

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    if (!canSubmit) {
      return;
    }

    setIsSubmitting(true);

    const trimmedEmail = email.trim();

    const result = await signup(trimmedEmail, password, {
      privacy: privacyConsent,
      external: externalConsent,
    });

    if (result.ok) {
      router.push("/settings/consent");
    } else {
      setError(result.error || "Failed to create account. Please try again.");
    }

    setIsSubmitting(false);
  };

  return (
    <div className="auth-shell">
      <div className="auth-panel">
        <section className="auth-showcase">
          <p className="page-kicker text-white/70 mb-4">Secure onboarding</p>
          <div className="flex items-center gap-4">
            <div className="sidebar-brand-mark">D</div>
            <h1 className="text-4xl font-bold tracking-tight text-white">Create your DevFolio workspace</h1>
          </div>
          <p className="mt-6 max-w-md text-sm leading-7 text-white/78">
            Build a polished portfolio analysis workspace with explicit consent controls and presentation-ready outputs.
          </p>
          <div className="mt-8 grid gap-3">
            <div className="auth-metric">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/62">Privacy</p>
              <p className="mt-1 text-sm text-white">Clear consent prompts for data storage and external AI services.</p>
            </div>
            <div className="auth-metric">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/62">Workflow</p>
              <p className="mt-1 text-sm text-white">Move from project scans to resumes and portfolio views in one system.</p>
            </div>
          </div>
        </section>

        <Card className="auth-card w-full border-0 bg-transparent">
          <CardHeader className="space-y-1 px-0 pt-0">
            <CardTitle className="text-3xl font-bold">
              Create an account
            </CardTitle>
            <CardDescription>
              Enter your details to get started
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4 px-0">
            {error && (
              <div
                data-testid="error-message"
                className="p-3 text-sm text-red-800 bg-red-50 border-2 border-red-300 rounded-md"
              >
                {error}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                data-testid="email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isSubmitting}
                autoComplete="email"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                data-testid="password"
                type="password"
                placeholder="Create a password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting}
                autoComplete="new-password"
              />
              {password.length > 0 && (
                <div data-testid="password-strength">
                  <PasswordStrength password={password} />
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm-password">Confirm Password</Label>
              <Input
                id="confirm-password"
                data-testid="confirm-password"
                type="password"
                placeholder="Confirm your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isSubmitting}
                autoComplete="new-password"
              />
              {confirmPassword.length > 0 && !passwordsMatch && (
                <p className="text-sm text-red-600">Passwords do not match</p>
              )}
            </div>

            <div className="space-y-3 pt-2">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start space-x-2">
                  <Checkbox
                    id="privacy-consent"
                    data-testid="privacy-consent"
                    checked={privacyConsent}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setPrivacyConsent(e.target.checked)}
                    disabled={isSubmitting}
                    className="mt-0.5"
                  />
                  <Label htmlFor="privacy-consent" className="text-sm font-normal cursor-pointer leading-tight">
                    I agree to the data consent notice
                  </Label>
                </div>
                <div className="relative">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-auto px-2 py-1 text-xs text-primary"
                    aria-expanded={activeNotice === "privacy"}
                    onClick={() => setActiveNotice(activeNotice === "privacy" ? null : "privacy")}
                  >
                    {activeNotice === "privacy" ? "Hide" : "Read"}
                  </Button>
                  {activeNotice === "privacy" && (
                    <div className="absolute right-0 z-20 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-md border-2 border-border bg-background p-4 text-sm text-muted-foreground sm:w-80">
                      <p className="font-semibold text-foreground">Data consent notice</p>
                      <p className="mt-2">
                        We store your email address and authentication tokens to create your account, sign you in, and
                        keep your session active. Consent records are linked to your user ID for compliance.
                      </p>
                      <p className="mt-2">
                        We do not sell personal data. You can review or withdraw consent in settings at any time; changes
                        apply to future processing.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start space-x-2">
                  <Checkbox
                    id="external-consent"
                    data-testid="external-consent"
                    checked={externalConsent}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setExternalConsent(e.target.checked)}
                    disabled={isSubmitting}
                    className="mt-0.5"
                  />
                  <Label htmlFor="external-consent" className="text-sm font-normal cursor-pointer leading-tight">
                    I allow external AI services for analysis (optional services)
                  </Label>
                </div>
                <div className="relative">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-auto px-2 py-1 text-xs text-primary"
                    aria-expanded={activeNotice === "external"}
                    onClick={() => setActiveNotice(activeNotice === "external" ? null : "external")}
                  >
                    {activeNotice === "external" ? "Hide" : "Read"}
                  </Button>
                  {activeNotice === "external" && (
                    <div className="absolute right-0 z-20 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-md border-2 border-border bg-background p-4 text-sm text-muted-foreground sm:w-80">
                      <p className="font-semibold text-foreground">External services consent</p>
                      <p className="mt-2">
                        When enabled, selected content you submit may be sent to external AI providers for analysis to
                        generate insights. This may include file names, text snippets, or metadata you choose to analyze.
                      </p>
                      <p className="mt-2">
                        You can opt out later and continue using local-only analysis features. We only send data for
                        features you explicitly use.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="remember-me"
                  data-testid="remember-me"
                  checked={rememberMe}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setRememberMe(e.target.checked)}
                  disabled={isSubmitting}
                />
                <Label htmlFor="remember-me" className="text-sm font-normal cursor-pointer">
                  Remember me
                </Label>
              </div>
            </div>
            </CardContent>

            <CardFooter className="flex flex-col space-y-4 px-0 pb-0">
              <Button
                type="submit"
                data-testid="submit"
                className="w-full"
                disabled={!canSubmit || isLoading}
              >
                {isSubmitting ? "Creating account..." : "Create account"}
              </Button>

              <p className="text-sm text-center text-muted-foreground">
                Already have an account?{" "}
                <Link href="/auth/login" className="text-primary hover:underline">
                  Log in
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
