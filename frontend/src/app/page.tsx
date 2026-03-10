"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle } from "lucide-react";

import { CapExLineChart } from "@/components/CapExLineChart";
import { CapExBarChart } from "@/components/CapExBarChart";
import { AnalysisDisplay } from "@/components/AnalysisDisplay";

import { Sidebar } from "@/components/Sidebar";
import { EmptyState } from "@/components/EmptyState";
import { ShimmerLoader } from "@/components/ShimmerLoader";
import { EconomicIndicatorsPanel } from "@/components/EconomicIndicatorsPanel";
import { analyzeCapEx, chatWithAnalysis } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { useSettings } from "@/hooks/useSettings";
import { useCapExData } from "@/hooks/useCapExData";
import { useEconomicIndicators } from "@/hooks/useEconomicIndicators";

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3 },
};

export default function Page() {
  const { settings, isConfigured } = useSettings();
  const { data, isLoading, error, fromCache, cacheDate, refresh, forceRefresh } =
    useCapExData();

  const latestPeriod = data?.quarters[data.quarters.length - 1]?.period ?? null;
  const { data: indicatorsData } = useEconomicIndicators();

  const [analysis, setAnalysis] = useState<string>("");
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [streamingAnswer, setStreamingAnswer] = useState<string>("");
  const [isAsking, setIsAsking] = useState<boolean>(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  const handleAnalyze = useCallback(async (): Promise<void> => {
    if (!settings || !isConfigured || !data) return;

    // Cancel any in-flight request
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    setIsAnalyzing(true);
    setAnalyzeError(null);
    setAnalysis("");
    // Reset Q&A when starting a fresh analysis
    setChatHistory([]);
    setStreamingAnswer("");

    try {
      const res = await analyzeCapEx(settings, data, abortControllerRef.current.signal);

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        setAnalyzeError(
          `Analysis failed (HTTP ${res.status}). ${text}`.trim()
        );
        setIsAnalyzing(false);
        return;
      }

      const contentType = res.headers.get("content-type") ?? "";

      // Handle plain JSON response (non-streaming)
      if (contentType.includes("application/json")) {
        const json = (await res.json()) as { analysis?: string; error?: string };
        if (json.error) {
          setAnalyzeError(json.error);
        } else {
          setAnalysis(json.analysis ?? "");
        }
        setIsAnalyzing(false);
        return;
      }

      // Handle SSE / text streaming
      const reader = res.body?.getReader();
      if (!reader) {
        setAnalyzeError("No response body received from the server.");
        setIsAnalyzing(false);
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const payload = line.slice(6).trim();
            if (payload === "[DONE]") break;
            try {
              const parsed = JSON.parse(payload) as {
                content?: string;
                error?: string;
              };
              if (parsed.error) {
                setAnalyzeError(parsed.error);
              } else if (parsed.content) {
                setAnalysis((prev) => prev + parsed.content);
              }
            } catch {
              // Non-JSON SSE line — append raw content
              if (payload && payload !== "[DONE]") {
                setAnalysis((prev) => prev + payload);
              }
            }
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      setAnalyzeError(`Analysis error: ${message}`);
    } finally {
      setIsAnalyzing(false);
    }
  }, [settings, isConfigured, data]);

  const handleAskQuestion = useCallback(async (question: string): Promise<void> => {
    if (!settings || !isConfigured || !analysis) return;

    const newHistory: ChatMessage[] = [
      ...chatHistory,
      { role: "user", content: question },
    ];
    setChatHistory(newHistory);
    setIsAsking(true);
    setStreamingAnswer("");

    try {
      const res = await chatWithAnalysis(settings, analysis, chatHistory, question);

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        setChatHistory([
          ...newHistory,
          { role: "assistant", content: `Error: ${text || `HTTP ${res.status}`}` },
        ]);
        setIsAsking(false);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        setIsAsking(false);
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";
      let answer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const payload = line.slice(6).trim();
            if (payload === "[DONE]") break;
            try {
              const parsed = JSON.parse(payload) as {
                content?: string;
                error?: string;
              };
              if (parsed.error) {
                answer += `\n\n_Error: ${parsed.error}_`;
              } else if (parsed.content) {
                answer += parsed.content;
                setStreamingAnswer(answer);
              }
            } catch {
              if (payload && payload !== "[DONE]") {
                answer += payload;
                setStreamingAnswer(answer);
              }
            }
          }
        }
      }

      setChatHistory([...newHistory, { role: "assistant", content: answer }]);
      setStreamingAnswer("");
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      setChatHistory([
        ...newHistory,
        { role: "assistant", content: `_Error: ${message}_` },
      ]);
    } finally {
      setIsAsking(false);
    }
  }, [settings, isConfigured, analysis, chatHistory]);

  const showEmptyState = !isLoading && !data && !analysis && !error;
  const showData = data !== null;

  return (
    <div className="flex h-full w-full overflow-hidden">
      <Sidebar
        onAnalyze={handleAnalyze}
        onRefresh={refresh}
        onForceRefresh={forceRefresh}
        isAnalyzing={isAnalyzing}
        isLoading={isLoading}
        fromCache={fromCache}
        cacheDate={cacheDate}
        latestPeriod={latestPeriod}
      />

      {/* Main content area */}
      <main
        className="dot-grid-bg relative flex flex-1 flex-col overflow-y-auto p-6 lg:p-8"
        aria-label="Main content"
        aria-live="polite"
      >
        {/* Mobile top spacing for hamburger button */}
        <div className="lg:hidden h-12" aria-hidden="true" />

        {/* Fetch error banner */}
        <AnimatePresence>
          {error && (
            <motion.div
              {...fadeInUp}
              exit={{ opacity: 0, y: -10 }}
              className="mb-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700"
              role="alert"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>
                {error} {fromCache && "Showing previously cached data."}
              </span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading skeleton */}
        {isLoading && !data && (
          <div className="grid gap-6 md:grid-cols-2">
            <ShimmerLoader variant="chart" className="h-64" />
            <ShimmerLoader variant="chart" className="h-64" />
          </div>
        )}

        {/* Empty state */}
        {showEmptyState && (
          <EmptyState className="flex-1" />
        )}

        {/* Data section */}
        {showData && (
          <motion.section
            {...fadeInUp}
            className="space-y-6"
            aria-label="Capital expenditure data"
          >
            {/* Chart grid */}
            <div className="grid gap-6 md:grid-cols-2">
              <CapExLineChart data={data} isLoading={isLoading} />
              <CapExBarChart data={data} isLoading={isLoading} />
            </div>

            {/* Economic context indicators */}
            {indicatorsData && (
              <EconomicIndicatorsPanel data={indicatorsData} />
            )}

            {/* Analysis section */}
            <AnimatePresence mode="wait">
              {isAnalyzing && !analysis && (
                <motion.div
                  key="analyzing"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-2"
                  aria-live="polite"
                  aria-label="Generating analysis"
                >
                  <p className="text-sm font-medium text-blue-600">
                    Analyzing…
                  </p>
                  <ShimmerLoader variant="card" />
                </motion.div>
              )}

              {analyzeError && !isAnalyzing && (
                <motion.div
                  key="analyze-error"
                  {...fadeInUp}
                  className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                  role="alert"
                >
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>{analyzeError}</span>
                </motion.div>
              )}

              {analysis && (
                <AnalysisDisplay
                  key="analysis"
                  analysis={analysis}
                  isStreaming={isAnalyzing}
                  chatHistory={chatHistory}
                  streamingAnswer={streamingAnswer}
                  isAsking={isAsking}
                  onAskQuestion={handleAskQuestion}
                />
              )}
            </AnimatePresence>
          </motion.section>
        )}
      </main>
    </div>
  );
}
