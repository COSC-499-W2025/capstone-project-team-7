import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lumen - Capstone Desktop",
  description: "Next.js renderer scaffold for the Electron migration"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 antialiased">
        {children}
      </body>
    </html>
  );
}
