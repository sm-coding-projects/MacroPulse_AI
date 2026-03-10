"use client";

import { useState, useEffect, useCallback } from "react";
import { getEconomicIndicators } from "@/lib/api";
import type { EconomicIndicatorsData } from "@/lib/types";

interface UseEconomicIndicatorsReturn {
  data: EconomicIndicatorsData | null;
  isLoading: boolean;
  error: string | null;
  fromCache: boolean;
  refresh: () => void;
}

export function useEconomicIndicators(): UseEconomicIndicatorsReturn {
  const [data, setData] = useState<EconomicIndicatorsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getEconomicIndicators();
      if (res.error && !res.data) {
        setError(res.error);
      } else {
        setData(res.data);
        setFromCache(res.from_cache);
        if (res.error) setError(res.error);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load indicators");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return { data, isLoading, error, fromCache, refresh: load };
}
