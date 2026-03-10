"use client";

import { useState, useEffect, useCallback } from "react";

import type { LLMSettings } from "@/lib/types";

const STORAGE_KEY = "macropulse_llm_settings";
// Custom event fired whenever this hook writes to localStorage so that all
// other instances of the hook on the same page can re-sync immediately.
const SYNC_EVENT = "macropulse:settings-changed";

function readFromStorage(): LLMSettings | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (
      parsed &&
      typeof parsed === "object" &&
      "base_url" in parsed &&
      "model" in parsed &&
      typeof (parsed as Record<string, unknown>).base_url === "string" &&
      typeof (parsed as Record<string, unknown>).model === "string"
    ) {
      return parsed as LLMSettings;
    }
  } catch {
    // Corrupt data — treat as empty
  }
  return null;
}

interface UseSettingsReturn {
  settings: LLMSettings | null;
  updateSettings: (s: LLMSettings) => void;
  clearSettings: () => void;
  isConfigured: boolean;
}

export function useSettings(): UseSettingsReturn {
  const [settings, setSettings] = useState<LLMSettings | null>(null);

  // Hydrate from localStorage on mount (avoids SSR mismatch)
  useEffect(() => {
    setSettings(readFromStorage());
  }, []);

  // Re-sync whenever another instance of this hook writes settings on this page
  useEffect(() => {
    function handleSync() {
      setSettings(readFromStorage());
    }
    window.addEventListener(SYNC_EVENT, handleSync);
    return () => window.removeEventListener(SYNC_EVENT, handleSync);
  }, []);

  const updateSettings = useCallback((s: LLMSettings): void => {
    setSettings(s);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
      window.dispatchEvent(new Event(SYNC_EVENT));
    }
  }, []);

  const clearSettings = useCallback((): void => {
    setSettings(null);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
      window.dispatchEvent(new Event(SYNC_EVENT));
    }
  }, []);

  const isConfigured = Boolean(
    settings?.base_url?.trim() &&
      settings?.api_key !== undefined &&
      settings?.model?.trim()
  );

  return { settings, updateSettings, clearSettings, isConfigured };
}
