"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { useAuth } from "@/hooks/use-auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
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
        <p className="text-sm text-muted-foreground">Loading...</p>
      </main>
    );
  }

  return (
    <>
      <Sidebar />
      <main className="ml-[280px]">
        {children}
      </main>
    </>
  );
}
