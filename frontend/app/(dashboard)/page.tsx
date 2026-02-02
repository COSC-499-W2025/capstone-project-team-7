"use client";

import { Plus } from "lucide-react";

export default function HomePage() {
  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center justify-between">
          <h1 className="text-4xl font-bold text-gray-900 tracking-tight">Dashboard</h1>
          <button className="flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors shadow-sm">
            <Plus size={20} />
            <span className="font-medium">New Scan</span>
          </button>
        </div>
      </div>
      {/* Empty space below for future widgets */}
    </div>
  );
}
