"use client";

import { useState, useEffect, useCallback } from "react";

import { fetchCapExData } from "@/lib/api";
import type { CapExData } from "@/lib/types";

interface UseCapExDataReturn {
  data: CapExData | null;
  isLoading: boolean;
  error: string | null;
  fromCache: boolean;
  cacheDate: string | null;
  refresh: () => void;
  forceRefresh: () => void;
}

export function useCapExData(): UseCapExDataReturn {
  const [data, setData] = useState<CapExData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState<boolean>(false);
  const [cacheDate, setCacheDate] = useState<string | null>(null);

  const load = useCallback(async (force: boolean): Promise<void> => {
    setIsLoading(true);
    setError(null);

    const response = await fetchCapExData(force);

    if (response.error) {
      setError(response.error);
      // Keep existing data visible if we have it (stale cache fallback)
    } else {
      setData(response.data);
    }

    setFromCache(response.from_cache);
    setCacheDate(response.cache_date);
    setIsLoading(false);
  }, []);

  const refresh = useCallback(() => load(false), [load]);
  const forceRefresh = useCallback(() => load(true), [load]);

  // Auto-fetch on mount
  useEffect(() => {
    refresh();
  }, [refresh]);

  return { data, isLoading, error, fromCache, cacheDate, refresh, forceRefresh };
}
