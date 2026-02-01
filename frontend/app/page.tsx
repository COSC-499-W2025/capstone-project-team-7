"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 max-w-2xl w-full text-center">
        <h1 className="text-4xl font-bold text-gray-900 tracking-tight mb-4">
          Welcome to Lumen
        </h1>
        <p className="text-gray-600 mb-8">
          Your capstone project portfolio and analysis platform
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/settings">
            <Button className="bg-gray-900 text-white hover:bg-gray-800">
              Go to Settings
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
