import type { Metadata } from "next";
import { Toaster } from "@/lib/notifications";
import "./globals.css";

export const metadata: Metadata = {
  title: "DevFolio",
  description: "AI-powered developer portfolio platform"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 antialiased">
        {children}
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
