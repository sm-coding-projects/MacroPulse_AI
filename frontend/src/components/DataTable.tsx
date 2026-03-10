"use client";

import { useState, useCallback, useId } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";

import { cn, formatCurrency, formatPercentChange, formatDate } from "@/lib/utils";
import type { CapExData, CapExQuarter } from "@/lib/types";

interface DataTableProps {
  data: CapExData;
  title: string;
  className?: string;
}

type SortKey = keyof CapExQuarter;
type SortDirection = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "period", label: "Period" },
  { key: "total", label: "Total" },
  { key: "mining", label: "Mining" },
  { key: "manufacturing", label: "Manufacturing" },
  { key: "other_selected", label: "Other Selected" },
  { key: "buildings_structures", label: "Buildings & Structures" },
  { key: "equipment_plant_machinery", label: "Equipment & Machinery" },
  { key: "qoq_change", label: "QoQ Change" },
  { key: "yoy_change", label: "YoY Change" },
];

function formatCellValue(key: SortKey, value: CapExQuarter[SortKey]): string {
  if (value === null || value === undefined) return "—";
  if (key === "period") return formatDate(value as string);
  if (key === "qoq_change" || key === "yoy_change") {
    return formatPercentChange(value as number);
  }
  return formatCurrency(value as number);
}

function sortQuarters(
  quarters: CapExQuarter[],
  sortKey: SortKey,
  sortDir: SortDirection
): CapExQuarter[] {
  return [...quarters].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];

    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;

    let comparison = 0;
    if (typeof aVal === "string" && typeof bVal === "string") {
      comparison = aVal.localeCompare(bVal);
    } else {
      comparison = (aVal as number) - (bVal as number);
    }

    return sortDir === "asc" ? comparison : -comparison;
  });
}

export function DataTable({ data, title, className }: DataTableProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("period");
  const [sortDir, setSortDir] = useState<SortDirection>("desc");

  const tableId = useId();
  const announcerId = useId();

  const handleToggle = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const handleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir("asc");
      }
    },
    [sortKey]
  );

  const sortedQuarters = sortQuarters(data.quarters, sortKey, sortDir);
  const announceText = isExpanded
    ? `${title} is now expanded`
    : `${title} is now collapsed`;

  return (
    <div className={cn("", className)}>
      {/* Screen reader live region */}
      <div
        id={announcerId}
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {announceText}
      </div>

      {/* Toggle button */}
      <button
        type="button"
        onClick={handleToggle}
        aria-expanded={isExpanded}
        aria-controls={tableId}
        className={cn(
          "flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium",
          "text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
        )}
      >
        {isExpanded ? (
          <ChevronUp className="h-3.5 w-3.5" aria-hidden="true" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
        )}
        {isExpanded ? "Hide data table" : "Show data table"}
      </button>

      {/* Animated collapsible table */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            id={tableId}
            key="table"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-3 overflow-x-auto rounded-lg border border-gray-200">
              <table
                role="table"
                aria-label={title}
                className="w-full min-w-[640px] border-collapse text-xs"
              >
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    {COLUMNS.map((col) => {
                      const isSorted = sortKey === col.key;
                      return (
                        <th
                          key={col.key}
                          scope="col"
                          aria-sort={
                            isSorted
                              ? sortDir === "asc"
                                ? "ascending"
                                : "descending"
                              : "none"
                          }
                          className={cn(
                            "whitespace-nowrap px-3 py-2 text-left font-semibold text-gray-600",
                            "cursor-pointer select-none transition-colors hover:text-gray-900",
                            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-slate-900"
                          )}
                          tabIndex={0}
                          onClick={() => handleSort(col.key)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              handleSort(col.key);
                            }
                          }}
                        >
                          <span className="flex items-center gap-1">
                            {col.label}
                            {isSorted && (
                              <span aria-hidden="true" className="text-slate-700">
                                {sortDir === "asc" ? " ↑" : " ↓"}
                              </span>
                            )}
                          </span>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {sortedQuarters.map((quarter, rowIndex) => (
                    <tr
                      key={quarter.period}
                      className={cn(
                        "border-b border-gray-100 transition-colors hover:bg-gray-50",
                        rowIndex % 2 === 0
                          ? "bg-white"
                          : "bg-gray-50/50"
                      )}
                    >
                      {COLUMNS.map((col) => {
                        const raw = quarter[col.key];
                        const formatted = formatCellValue(col.key, raw);
                        const isChange =
                          col.key === "qoq_change" || col.key === "yoy_change";
                        const numVal =
                          isChange && raw !== null ? (raw as number) : null;

                        return (
                          <td
                            key={col.key}
                            className={cn(
                              "whitespace-nowrap px-3 py-2 text-gray-700",
                              col.key === "period" && "font-medium text-gray-900",
                              isChange &&
                                numVal !== null &&
                                numVal >= 0 &&
                                "text-emerald-600",
                              isChange &&
                                numVal !== null &&
                                numVal < 0 &&
                                "text-red-600"
                            )}
                          >
                            {formatted}
                          </td>
                        );
                      })}
                    </tr>
                  ))}

                  {sortedQuarters.length === 0 && (
                    <tr>
                      <td
                        colSpan={COLUMNS.length}
                        className="px-3 py-6 text-center text-gray-500"
                      >
                        No data available
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
