"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { CornerRightUp, Mic } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/types";

interface AnalysisDisplayProps {
  analysis: string;
  isStreaming?: boolean;
  chatHistory: ChatMessage[];
  streamingAnswer: string;
  isAsking: boolean;
  onAskQuestion: (question: string) => void;
  className?: string;
}

// ---------------------------------------------------------------------------
// Auto-resize hook — grows textarea from minHeight up to maxHeight
// ---------------------------------------------------------------------------
function useAutoResize({
  minHeight,
  maxHeight,
}: {
  minHeight: number;
  maxHeight: number;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback(
    (reset?: boolean) => {
      const el = textareaRef.current;
      if (!el) return;
      el.style.height = `${minHeight}px`;
      if (reset) return;
      el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
    },
    [minHeight, maxHeight]
  );

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = `${minHeight}px`;
    }
  }, [minHeight]);

  useEffect(() => {
    const handler = () => adjustHeight();
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, [adjustHeight]);

  return { textareaRef, adjustHeight };
}

// ---------------------------------------------------------------------------
// Markdown renderer configs
// ---------------------------------------------------------------------------
const markdownComponents: Components = {
  h1: ({ children, ...props }) => (
    <h1 className="mb-3 mt-6 text-xl font-semibold text-gray-900 first:mt-0" {...props}>
      {children}
    </h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 className="mb-2 mt-6 text-lg font-semibold text-gray-900 first:mt-0" {...props}>
      {children}
    </h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 className="mb-2 mt-4 text-base font-semibold text-gray-800" {...props}>
      {children}
    </h3>
  ),
  p: ({ children, ...props }) => (
    <p className="mb-4 leading-relaxed text-gray-700 last:mb-0" {...props}>
      {children}
    </p>
  ),
  strong: ({ children, ...props }) => (
    <strong className="font-semibold text-gray-900" {...props}>{children}</strong>
  ),
  em: ({ children, ...props }) => (
    <em className="italic text-gray-700" {...props}>{children}</em>
  ),
  ul: ({ children, ...props }) => (
    <ul className="mb-4 ml-4 list-disc space-y-1 text-gray-700 marker:text-gray-400" {...props}>
      {children}
    </ul>
  ),
  ol: ({ children, ...props }) => (
    <ol className="mb-4 ml-4 list-decimal space-y-1 text-gray-700 marker:text-gray-400" {...props}>
      {children}
    </ol>
  ),
  li: ({ children, ...props }) => (
    <li className="leading-relaxed text-gray-700" {...props}>{children}</li>
  ),
  blockquote: ({ children, ...props }) => (
    <blockquote className="my-4 border-l-2 border-gray-300 pl-4 italic text-gray-600" {...props}>
      {children}
    </blockquote>
  ),
  code: ({ children, ...props }) => (
    <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs text-gray-800" {...props}>
      {children}
    </code>
  ),
  pre: ({ children, ...props }) => (
    <pre className="mb-4 overflow-x-auto rounded-lg bg-gray-100 p-4 font-mono text-xs text-gray-800" {...props}>
      {children}
    </pre>
  ),
  table: ({ children, ...props }) => (
    <div className="mb-4 overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full border-collapse text-sm text-gray-700" {...props}>
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }) => (
    <thead className="border-b border-gray-200 bg-gray-50 text-gray-800" {...props}>{children}</thead>
  ),
  th: ({ children, ...props }) => (
    <th className="border border-gray-200 px-3 py-2 text-left font-semibold" {...props}>{children}</th>
  ),
  td: ({ children, ...props }) => (
    <td className="border border-gray-100 px-3 py-2" {...props}>{children}</td>
  ),
  hr: ({ ...props }) => <hr className="my-6 border-gray-200" {...props} />,
  a: ({ children, href, ...props }) => (
    <a
      href={href}
      className="text-blue-600 underline hover:text-blue-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 rounded"
      target="_blank"
      rel="noopener noreferrer"
      {...props}
    >
      {children}
    </a>
  ),
};

// Compact markdown for chat bubbles
const chatMarkdownComponents: Components = {
  ...markdownComponents,
  h1: ({ children, ...props }) => (
    <h1 className="mb-1 text-base font-semibold text-gray-800" {...props}>{children}</h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 className="mb-1 text-sm font-semibold text-gray-800" {...props}>{children}</h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 className="mb-1 text-sm font-semibold text-gray-700" {...props}>{children}</h3>
  ),
  p: ({ children, ...props }) => (
    <p className="mb-2 text-sm leading-relaxed text-gray-700 last:mb-0" {...props}>{children}</p>
  ),
  ul: ({ children, ...props }) => (
    <ul className="mb-2 ml-4 list-disc space-y-0.5 text-sm text-gray-700 marker:text-gray-400" {...props}>
      {children}
    </ul>
  ),
  ol: ({ children, ...props }) => (
    <ol className="mb-2 ml-4 list-decimal space-y-0.5 text-sm text-gray-700 marker:text-gray-400" {...props}>
      {children}
    </ol>
  ),
  li: ({ children, ...props }) => (
    <li className="text-sm leading-relaxed text-gray-700" {...props}>{children}</li>
  ),
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function AnalysisDisplay({
  analysis,
  isStreaming = false,
  chatHistory,
  streamingAnswer,
  isAsking,
  onAskQuestion,
  className,
}: AnalysisDisplayProps) {
  const isEmpty = !analysis || analysis.trim().length === 0;
  const showChat = !isEmpty && !isStreaming;

  const [inputText, setInputText] = useState<string>("");
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const { textareaRef, adjustHeight } = useAutoResize({
    minHeight: 52,
    maxHeight: 200,
  });

  // Scroll to bottom whenever chat updates
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, streamingAnswer, isAsking]);

  function handleSubmit() {
    const question = inputText.trim();
    if (!question || isAsking) return;
    setInputText("");
    adjustHeight(true);
    onAskQuestion(question);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.2 }}
      className={className}
    >
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm font-medium tracking-tight text-gray-900">
              AI Analysis
            </CardTitle>
            {isStreaming && (
              <span
                className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-600"
                aria-live="polite"
                aria-label="Generating analysis"
              >
                <span
                  className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500"
                  aria-hidden="true"
                />
                Generating
              </span>
            )}
          </div>
        </CardHeader>

        <CardContent>
          {isEmpty ? (
            <p className="text-sm text-gray-500">
              No analysis available. Configure your LLM settings and click Analyze to generate insights.
            </p>
          ) : (
            <div
              aria-live="polite"
              aria-atomic="false"
              aria-label="AI-generated analysis content"
              className="min-h-0"
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {isStreaming ? `${analysis}▊` : analysis}
              </ReactMarkdown>
            </div>
          )}

          {/* Disclaimer */}
          <div className={cn("mt-6 border-t border-gray-200 pt-4", isEmpty && "mt-0 border-t-0 pt-0")}>
            <p className="text-xs leading-relaxed text-gray-500">
              This analysis is AI-generated based on ABS data and may contain errors. It does not
              constitute financial advice. Verify all figures against the source data displayed above.
            </p>
          </div>

          {/* Follow-up Q&A */}
          {showChat && (
            <div className="mt-6 border-t border-gray-200 pt-4">
              <h3 className="mb-3 text-sm font-medium text-gray-900">
                Ask a follow-up question
              </h3>

              {/* Chat history */}
              {(chatHistory.length > 0 || isAsking) && (
                <div
                  className="mb-4 max-h-96 space-y-3 overflow-y-auto pr-1"
                  aria-label="Conversation history"
                  aria-live="polite"
                >
                  {chatHistory.map((message, i) => (
                    <div
                      key={i}
                      className={cn(
                        "flex",
                        message.role === "user" ? "justify-end" : "justify-start"
                      )}
                    >
                      {message.role === "user" ? (
                        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-slate-900 px-3 py-2 text-sm text-white">
                          {message.content}
                        </div>
                      ) : (
                        <div className="max-w-[80%] rounded-2xl rounded-tl-sm bg-gray-100 px-3 py-2">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={chatMarkdownComponents}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                  ))}

                  {streamingAnswer && (
                    <div className="flex justify-start">
                      <div className="max-w-[80%] rounded-2xl rounded-tl-sm bg-gray-100 px-3 py-2">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={chatMarkdownComponents}
                        >
                          {`${streamingAnswer}▊`}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}

                  {isAsking && !streamingAnswer && (
                    <div className="flex justify-start" aria-label="Generating response">
                      <div className="rounded-2xl rounded-tl-sm bg-gray-100 px-3 py-3">
                        <span className="flex gap-1" aria-hidden="true">
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: "0ms" }} />
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: "150ms" }} />
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: "300ms" }} />
                        </span>
                      </div>
                    </div>
                  )}

                  <div ref={chatBottomRef} />
                </div>
              )}

              {/* ---- Prompt input (21st.dev #976 design) ---- */}
              <div className="relative w-full">
                <textarea
                  ref={textareaRef}
                  value={inputText}
                  onChange={(e) => {
                    setInputText(e.target.value);
                    adjustHeight();
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about this data…"
                  disabled={isAsking}
                  aria-label="Follow-up question input"
                  className={cn(
                    "w-full rounded-3xl bg-black/5",
                    "pl-6 pr-16 py-[16px]",
                    "text-sm text-black leading-[1.2]",
                    "placeholder:text-black/50",
                    "border-none outline-none ring-1 ring-black/10",
                    "overflow-y-auto resize-none",
                    "transition-[height] duration-100 ease-out",
                    "focus:ring-black/20",
                    "disabled:cursor-not-allowed disabled:opacity-50",
                    "[&::-webkit-resizer]:hidden"
                  )}
                  style={{ minHeight: 52, maxHeight: 200 }}
                />

                {/* Mic icon — slides left when text is present */}
                <div
                  className={cn(
                    "absolute top-1/2 -translate-y-1/2 rounded-xl bg-black/5 px-1 py-1",
                    "transition-all duration-200",
                    inputText ? "right-10" : "right-3"
                  )}
                  aria-hidden="true"
                >
                  <Mic className="h-4 w-4 text-black/70" />
                </div>

                {/* Submit button — fades in when text is present */}
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={isAsking || !inputText.trim()}
                  aria-label="Send question"
                  className={cn(
                    "absolute top-1/2 -translate-y-1/2 right-3",
                    "rounded-xl bg-black/5 px-1 py-1",
                    "transition-all duration-200",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900",
                    inputText.trim()
                      ? "opacity-100 scale-100"
                      : "opacity-0 scale-95 pointer-events-none"
                  )}
                >
                  <CornerRightUp className="h-4 w-4 text-black/70" />
                </button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
