import * as React from "react";

import { cn } from "@/lib/utils";

interface ShimmerLoaderProps {
  className?: string;
  lines?: number;
  variant?: "line" | "card" | "chart";
}

function ShimmerBar({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "h-4 animate-pulse rounded-md bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 bg-[length:200%_100%]",
        className
      )}
      aria-hidden="true"
    />
  );
}

export function ShimmerLoader({
  className,
  lines = 3,
  variant = "line",
}: ShimmerLoaderProps) {
  if (variant === "chart") {
    return (
      <div
        className={cn(
          "rounded-xl border border-gray-200 bg-white p-6",
          className
        )}
        role="status"
        aria-label="Loading chart data"
      >
        <ShimmerBar className="mb-4 h-5 w-1/3" />
        <div className="flex items-end gap-2 pt-4">
          {[80, 120, 60, 100, 140, 90, 110, 75].map((height, i) => (
            <div
              key={i}
              className="animate-pulse rounded-t-sm bg-gradient-to-t from-gray-200 via-gray-100 to-gray-200 flex-1"
              style={{ height: `${height}px` }}
              aria-hidden="true"
            />
          ))}
        </div>
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div
        className={cn(
          "rounded-xl border border-gray-200 bg-white p-6 space-y-4",
          className
        )}
        role="status"
        aria-label="Loading content"
      >
        <ShimmerBar className="h-5 w-2/5" />
        <ShimmerBar className="h-4 w-full" />
        <ShimmerBar className="h-4 w-5/6" />
        <ShimmerBar className="h-4 w-3/4" />
      </div>
    );
  }

  // Default: line variant
  return (
    <div
      className={cn("space-y-3", className)}
      role="status"
      aria-label="Loading"
    >
      {Array.from({ length: lines }).map((_, i) => (
        <ShimmerBar
          key={i}
          className={
            i === lines - 1 && lines > 1 ? "w-4/5" : "w-full"
          }
        />
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}
