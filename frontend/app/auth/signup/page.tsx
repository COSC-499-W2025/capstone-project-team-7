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

  if (isLoading || isAuthenticated) {
    return null;
  }

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

  const passwordsMatch = password === confirmPassword && confirmPassword.length > 0;

  const canSubmit =
    isEmailValid &&
    passwordValidation.isValid &&
    passwordsMatch &&
    privacyConsent &&
    externalConsent &&
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
      router.push("/");
    } else {
      setError(result.error || "Failed to create account. Please try again.");
    }

    setIsSubmitting(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            Create an account
          </CardTitle>
          <CardDescription className="text-center">
            Enter your details to get started
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <div
                data-testid="error-message"
                className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md"
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
                    <div className="absolute right-0 z-20 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-lg border border-border/70 bg-background p-4 text-sm text-muted-foreground shadow-lg sm:w-80">
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
                    <div className="absolute right-0 z-20 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-lg border border-border/70 bg-background p-4 text-sm text-muted-foreground shadow-lg sm:w-80">
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

          <CardFooter className="flex flex-col space-y-4">
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
  );
}
