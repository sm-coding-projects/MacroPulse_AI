import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface DataStatusBadgeProps {
  fromCache: boolean;
  cacheDate: string | null;
  isLoading: boolean;
  className?: string;
}

function formatCacheDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-AU", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

export function DataStatusBadge({
  fromCache,
  cacheDate,
  isLoading,
  className,
}: DataStatusBadgeProps) {
  if (isLoading) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <span
          className="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-500"
          aria-hidden="true"
        />
        <span className="text-xs text-gray-500">Fetching…</span>
      </div>
    );
  }

  if (fromCache && cacheDate) {
    return (
      <Badge variant="warning" className={className} title={`Cached data from ${cacheDate}`}>
        Cached {formatCacheDate(cacheDate)}
      </Badge>
    );
  }

  if (!fromCache) {
    return (
      <Badge variant="success" className={className}>
        Live data
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className={className}>
      No data
    </Badge>
  );
}
