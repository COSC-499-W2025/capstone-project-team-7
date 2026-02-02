import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";

export const metadata: Metadata = {
  title: "Lumen - Capstone Desktop",
  description: "Next.js renderer scaffold for the Electron migration"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 antialiased">
        <Sidebar />
        <main className="ml-[280px]">
          {children}
        </main>
      </body>
    </html>
  );
}
