"use client";

import { useState } from "react";
import { Menu, Zap, BarChart3, RefreshCw, Settings, ChevronDown, ChevronRight, Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { DataStatusBadge } from "@/components/DataStatusBadge";
import { SettingsPanel } from "@/components/SettingsPanel";
import { cn } from "@/lib/utils";
import { useSettings } from "@/hooks/useSettings";

interface SidebarProps {
  onAnalyze: () => void;
  onRefresh: () => void;
  onForceRefresh: () => void;
  isAnalyzing: boolean;
  isLoading: boolean;
  fromCache: boolean;
  cacheDate: string | null;
  latestPeriod: string | null;
  className?: string;
}

function SidebarContent({
  onAnalyze,
  onRefresh,
  onForceRefresh,
  isAnalyzing,
  isLoading,
  fromCache,
  cacheDate,
  latestPeriod,
}: Omit<SidebarProps, "className">) {
  const { isConfigured } = useSettings();
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto">
      {/* Logo */}
      <div className="flex items-center gap-2 pb-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900">
          <Zap className="h-4 w-4 text-white" aria-hidden="true" />
        </div>
        <span className="text-base font-semibold tracking-tight text-gray-900">
          MacroPulse AI
        </span>
      </div>

      <div className="h-px bg-gray-200" />

      {/* Data status */}
      <div className="flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-gray-400" aria-hidden="true" />
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
          Data Status
        </span>
      </div>
      <DataStatusBadge
        fromCache={fromCache}
        cacheDate={cacheDate}
        isLoading={isLoading}
      />

      <div className="h-px bg-gray-200" />

      {/* Primary action */}
      <Button
        variant="default"
        size="default"
        onClick={onAnalyze}
        disabled={!isConfigured || isAnalyzing || isLoading}
        className="relative w-full overflow-hidden"
        aria-label="Analyze latest CapEx data"
      >
        {isAnalyzing && (
          <span
            className="animate-shimmer-sweep absolute inset-0 bg-gradient-to-r from-transparent via-white/25 to-transparent"
            aria-hidden="true"
          />
        )}
        {isAnalyzing ? (
          <>
            <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
            Analyzing…
          </>
        ) : (
          <>
            <Zap className="h-4 w-4" aria-hidden="true" />
            Analyze Latest CapEx Data
          </>
        )}
      </Button>

      {!isConfigured && (
        <p className="text-xs text-gray-500 text-center">
          Configure your LLM below to enable analysis.
        </p>
      )}

      {/* Secondary action */}
      <Button
        variant="outline"
        size="sm"
        onClick={onRefresh}
        disabled={isLoading}
        className="w-full"
        aria-label="Refresh ABS data"
      >
        <RefreshCw
          className={cn("h-4 w-4", isLoading && "animate-spin")}
          aria-hidden="true"
        />
        Refresh Data
      </Button>

      {/* Force-refresh from ABS */}
      <Button
        variant="outline"
        size="sm"
        onClick={onForceRefresh}
        disabled={isLoading}
        className="w-full"
        aria-label="Fetch latest data directly from ABS, bypassing cache"
      >
        <Download
          className={cn("h-4 w-4", isLoading && "animate-pulse")}
          aria-hidden="true"
        />
        Fetch Latest from ABS
      </Button>

      {latestPeriod && (
        <p className="text-xs text-gray-500 text-center">
          Latest ABS data: <span className="font-medium text-gray-700">{latestPeriod}</span>
        </p>
      )}

      <div className="h-px bg-gray-200" />

      {/* Collapsible settings */}
      <button
        type="button"
        onClick={() => setSettingsOpen((v) => !v)}
        className="flex w-full items-center gap-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 focus-visible:ring-offset-white rounded"
        aria-expanded={settingsOpen}
        aria-controls="settings-panel"
      >
        <Settings className="h-4 w-4 text-gray-400" aria-hidden="true" />
        <span className="flex-1 text-sm font-medium text-gray-700">
          LLM Settings
        </span>
        {settingsOpen ? (
          <ChevronDown className="h-4 w-4 text-gray-400" aria-hidden="true" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400" aria-hidden="true" />
        )}
      </button>

      {settingsOpen && (
        <div id="settings-panel">
          <SettingsPanel />
        </div>
      )}
    </div>
  );
}

export function Sidebar({
  onAnalyze,
  onRefresh,
  onForceRefresh,
  isAnalyzing,
  isLoading,
  fromCache,
  cacheDate,
  latestPeriod,
  className,
}: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState<boolean>(false);

  const contentProps = {
    onAnalyze,
    onRefresh,
    onForceRefresh,
    isAnalyzing,
    isLoading,
    fromCache,
    cacheDate,
    latestPeriod,
  };

  return (
    <>
      {/* Mobile: hamburger trigger + Sheet */}
      <div className="lg:hidden">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation sidebar"
          className="fixed left-4 top-4 z-40"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </Button>

        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetContent side="left" className="w-72 bg-white p-6">
            <SheetHeader className="mb-4">
              <SheetTitle className="sr-only">Navigation</SheetTitle>
              <SheetDescription className="sr-only">
                Sidebar with LLM settings and data controls
              </SheetDescription>
            </SheetHeader>
            <SidebarContent {...contentProps} />
          </SheetContent>
        </Sheet>
      </div>

      {/* Desktop: fixed sidebar */}
      <aside
        className={cn(
          "hidden lg:flex flex-col w-72 shrink-0 border-r border-gray-200 bg-white p-6",
          className
        )}
        aria-label="Application sidebar"
      >
        <SidebarContent {...contentProps} />
      </aside>
    </>
  );
}
