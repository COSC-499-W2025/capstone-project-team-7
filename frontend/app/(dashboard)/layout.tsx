"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { useAuth } from "@/hooks/use-auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (typeof window !== "undefined") {
      const hash = window.location.hash;
      if (hash) {
        const params = new URLSearchParams(hash.slice(1));
        const accessToken = params.get("access_token");
        const type = params.get("type");
        if (accessToken && type === "recovery") {
          router.replace(`/auth/reset-password?access_token=${encodeURIComponent(accessToken)}`);
          return;
        }
      }
    }

    if (!isLoading && !isAuthenticated) {
      router.replace("/auth/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <main
        className="min-h-screen flex items-center justify-center"
        role="status"
        aria-busy="true"
        aria-live="polite"
      >
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-2 border-primary border-t-transparent mx-auto mb-4" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </main>
    );
  }

  return (
    <>
      <Sidebar />
      <main className="dashboard-stage">
        {children}
      </main>
    </>
  );
}
