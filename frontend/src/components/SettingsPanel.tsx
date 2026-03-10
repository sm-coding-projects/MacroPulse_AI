"use client";

import { useState, useEffect } from "react";
import { CheckCircle2, XCircle, Loader2, Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { testLLMConnection } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useSettings } from "@/hooks/useSettings";
import type { LLMSettings } from "@/lib/types";

interface SettingsPanelProps {
  className?: string;
}

type TestStatus = "idle" | "testing" | "success" | "error";

export function SettingsPanel({ className }: SettingsPanelProps) {
  const { settings, updateSettings, clearSettings } = useSettings();

  const [baseUrl, setBaseUrl] = useState<string>(
    settings?.base_url ?? ""
  );
  const [apiKey, setApiKey] = useState<string>(settings?.api_key ?? "");
  const [model, setModel] = useState<string>(settings?.model ?? "");

  const [testStatus, setTestStatus] = useState<TestStatus>("idle");
  const [testError, setTestError] = useState<string | null>(null);

  // Sync inputs when settings hydrate from localStorage on page load,
  // or when they are cleared from another component via the sync event.
  useEffect(() => {
    setBaseUrl(settings?.base_url ?? "");
    setApiKey(settings?.api_key ?? "");
    setModel(settings?.model ?? "");
  }, [settings]);

  const isSaveDisabled = !baseUrl.trim() || !model.trim();

  async function handleTestConnection(): Promise<void> {
    setTestStatus("testing");
    setTestError(null);

    const current: LLMSettings = {
      base_url: baseUrl.trim(),
      api_key: apiKey,
      model: model.trim(),
    };

    const result = await testLLMConnection(current);

    if (result.success) {
      setTestStatus("success");
    } else {
      setTestStatus("error");
      setTestError(result.error ?? "Connection test failed.");
    }
  }

  function handleSave(): void {
    const next: LLMSettings = {
      base_url: baseUrl.trim(),
      api_key: apiKey,
      model: model.trim(),
    };
    updateSettings(next);
    // Re-run test after save if it was previously in error state
    if (testStatus === "error") {
      setTestStatus("idle");
      setTestError(null);
    }
  }

  function handleClear(): void {
    clearSettings();
    setBaseUrl("");
    setApiKey("");
    setModel("");
    setTestStatus("idle");
    setTestError(null);
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div className="space-y-1.5">
        <Label htmlFor="llm-base-url">LLM Base URL</Label>
        <Input
          id="llm-base-url"
          type="text"
          placeholder="https://api.openai.com/v1"
          value={baseUrl}
          onChange={(e) => {
            setBaseUrl(e.target.value);
            setTestStatus("idle");
          }}
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="llm-api-key">API Key</Label>
        <Input
          id="llm-api-key"
          type="password"
          placeholder="sk-..."
          value={apiKey}
          onChange={(e) => {
            setApiKey(e.target.value);
            setTestStatus("idle");
          }}
          autoComplete="current-password"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="llm-model">Model Name</Label>
        <Input
          id="llm-model"
          type="text"
          placeholder="gpt-4o"
          value={model}
          onChange={(e) => {
            setModel(e.target.value);
            setTestStatus("idle");
          }}
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      {/* Connection test status */}
      {testStatus === "success" && (
        <div
          className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
          role="status"
          aria-live="polite"
        >
          <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden="true" />
          Connection verified.
        </div>
      )}

      {testStatus === "error" && testError && (
        <div
          className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          role="alert"
          aria-live="assertive"
        >
          <XCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{testError}</span>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-col gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleTestConnection}
          disabled={isSaveDisabled || testStatus === "testing"}
          className="w-full"
          aria-label="Test LLM connection"
        >
          {testStatus === "testing" ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Testing…
            </>
          ) : (
            "Test Connection"
          )}
        </Button>

        <Button
          type="button"
          variant="default"
          size="sm"
          onClick={handleSave}
          disabled={isSaveDisabled}
          className="w-full"
          aria-label="Save LLM settings"
        >
          Save Settings
        </Button>
      </div>

      <button
        type="button"
        onClick={handleClear}
        className="text-xs text-gray-500 underline underline-offset-2 hover:text-gray-700 transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
        aria-label="Clear saved LLM settings"
      >
        Clear Settings
      </button>

      {/* Privacy notice */}
      <div className="flex items-start gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
        <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-400" aria-hidden="true" />
        <p className="text-xs leading-relaxed text-gray-500">
          Your API key is stored locally in your browser and is never sent to
          our servers. It is transmitted directly to the LLM endpoint you
          configure.
        </p>
      </div>
    </div>
  );
}
