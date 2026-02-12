"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { useAuth } from "@/hooks/use-auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [isRedirecting, setIsRedirecting] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !isRedirecting) {
      setIsRedirecting(true);
      // Wait a moment for toast to display, then redirect
      const timer = setTimeout(() => {
        router.replace("/auth/login");
      }, 1500);
      
      return () => clearTimeout(timer);
    }
  }, [isAuthenticated, isLoading, router, isRedirecting]);

  if (isLoading || !isAuthenticated || isRedirecting) {
    return (
      <main
        className="min-h-screen flex items-center justify-center"
        role="status"
        aria-busy="true"
        aria-live="polite"
      >
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-2 border-primary border-t-transparent mx-auto mb-4" />
          <p className="text-sm text-muted-foreground">
            {isRedirecting ? "Redirecting to login..." : "Loading..."}
          </p>
        </div>
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
