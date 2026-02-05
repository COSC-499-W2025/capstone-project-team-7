"use client";

import React from "react";

interface ScanProgressProps {
  percent?: number;
  message?: string;
}

export function ScanProgress({ percent, message }: ScanProgressProps) {
  const isIndeterminate = percent === undefined || percent < 0;
  const displayPercent = isIndeterminate ? 0 : Math.min(100, Math.max(0, percent));

  return (
    <div className="w-full space-y-2">
      {/* Progress bar container */}
      <div className="h-2.5 w-full bg-gray-200 rounded-full overflow-hidden">
        {isIndeterminate ? (
          // Indeterminate animation
          <div className="h-full w-1/3 bg-gray-900 rounded-full animate-pulse" 
               style={{ animation: "indeterminate 1.5s ease-in-out infinite" }} />
        ) : (
          // Determinate progress
          <div
            className="h-full bg-gray-900 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${displayPercent}%` }}
          />
        )}
      </div>

      {/* Progress info */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600 truncate max-w-[80%]">
          {message || (isIndeterminate ? "Starting scan..." : "Processing...")}
        </span>
        {!isIndeterminate && (
          <span className="text-gray-900 font-medium">{Math.round(displayPercent)}%</span>
        )}
      </div>

      <style jsx>{`
        @keyframes indeterminate {
          0% {
            transform: translateX(-100%);
          }
          50% {
            transform: translateX(200%);
          }
          100% {
            transform: translateX(-100%);
          }
        }
      `}</style>
    </div>
  );
}
