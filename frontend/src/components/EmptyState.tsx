"use client";

import { motion } from "framer-motion";
import { BarChart3 } from "lucide-react";

import { cn } from "@/lib/utils";

interface EmptyStateProps {
  className?: string;
}

export function EmptyState({ className }: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white px-8 py-20 text-center",
        className
      )}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-gray-200 bg-gray-50"
      >
        <BarChart3 className="h-8 w-8 text-slate-600" aria-hidden="true" />
      </motion.div>

      <motion.h2
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.15 }}
        className="mb-3 text-xl font-semibold text-gray-900"
      >
        Ready to Analyze
      </motion.h2>

      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.2 }}
        className="max-w-sm text-sm leading-relaxed text-gray-500"
      >
        Connect your LLM in Settings, then click &ldquo;Analyze&rdquo; to get
        started.
      </motion.p>
    </motion.div>
  );
}
