"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setError("Email is required");
      setIsSubmitting(false);
      return;
    }

    if (!emailRegex.test(trimmedEmail)) {
      setError("Enter a valid email address");
      setIsSubmitting(false);
      return;
    }

    const redirectTo = typeof window !== "undefined"
      ? `${window.location.origin}/auth/reset-password`
      : undefined;

    const result = await api.auth.requestPasswordReset(trimmedEmail, redirectTo);

    if (result.ok) {
      setSuccess("If that email exists, a reset link has been sent.");
      setEmail("");
    } else {
      setError(result.error || "Unable to request a password reset. Please try again.");
    }

    setIsSubmitting(false);
  };

  return (
    <div className="auth-shell">
      <div className="auth-panel">
        <section className="auth-showcase">
          <p className="page-kicker text-white/70">Account recovery</p>
          <h1 className="text-4xl font-bold text-white">Reset access securely</h1>
          <p className="mt-4 max-w-md text-sm leading-7 text-white/78">
            Request a reset link and return to your portfolio, project, and resume workflow without losing momentum.
          </p>
        </section>

        <Card className="auth-card w-full border-0 bg-transparent">
          <CardHeader className="space-y-1 px-0 pt-0">
            <CardTitle className="text-3xl font-bold">Reset password</CardTitle>
            <CardDescription>
              Enter your email and we will send you a reset link.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4 px-0">
            {error && (
              <div className="p-3 text-sm text-red-800 bg-red-50 border-2 border-red-300 rounded-md">
                {error}
              </div>
            )}
            {success && (
              <div className="p-3 text-sm text-emerald-800 bg-emerald-50 border-2 border-emerald-300 rounded-md">
                {success}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isSubmitting}
                autoComplete="email"
              />
            </div>
            </CardContent>
            <CardFooter className="flex flex-col space-y-4 px-0 pb-0">
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Sending reset link..." : "Send reset link"}
              </Button>
              <Link href="/auth/login" className="text-sm text-primary hover:underline">
                Back to login
              </Link>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
