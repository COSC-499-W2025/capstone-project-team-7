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
    <div className="w-full space-y-3">
      <div className="relative h-2.5 w-full overflow-hidden rounded-full border border-border bg-muted/80">
        {isIndeterminate ? (
          <div
            className="absolute inset-y-0 left-0 w-[42%] rounded-full bg-gradient-to-r from-foreground via-foreground/75 to-transparent"
            style={{ animation: "indeterminate 1.3s cubic-bezier(0.45, 0.05, 0.55, 0.95) infinite" }}
          />
        ) : (
          <div
            className="h-full rounded-full bg-gradient-to-r from-foreground to-foreground/75 transition-all duration-500 ease-out"
            style={{ width: `${displayPercent}%` }}
          />
        )}
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="truncate max-w-[80%] text-muted-foreground">
          {message || (isIndeterminate ? "Starting scan..." : "Processing...")}
        </span>
        {!isIndeterminate && (
          <span className="font-semibold text-foreground">{Math.round(displayPercent)}%</span>
        )}
      </div>

      <style jsx>{`
        @keyframes indeterminate {
          0% {
            transform: translateX(-110%);
          }
          60% {
            transform: translateX(165%);
          }
          100% {
            transform: translateX(230%);
          }
        }
      `}</style>
    </div>
  );
}
