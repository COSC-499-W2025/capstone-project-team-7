import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Capstone Desktop",
  description: "Next.js renderer scaffold for the Electron migration"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-50 antialiased">
        <div className="mx-auto max-w-5xl px-6 py-12">{children}</div>
      </body>
    </html>
  );
}
