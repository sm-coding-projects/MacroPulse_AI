"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ShimmerLoader } from "@/components/ShimmerLoader";
import { DataTable } from "@/components/DataTable";
import { cn, formatCurrency, formatDate } from "@/lib/utils";
import type { CapExData } from "@/lib/types";

interface CapExLineChartProps {
  data: CapExData;
  isLoading?: boolean;
  className?: string;
}

interface TooltipPayloadEntry {
  name: string;
  value: number;
  color: string;
  dataKey: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div
      className="rounded-lg border border-gray-200 bg-white p-3 shadow-md"
      role="tooltip"
    >
      <p className="mb-2 text-xs font-semibold text-gray-700">{label}</p>
      <ul className="space-y-1">
        {payload.map((entry) => (
          <li key={entry.dataKey} className="flex items-center gap-2 text-xs">
            <span
              className="inline-block h-2 w-2 rounded-full shrink-0"
              style={{ backgroundColor: entry.color }}
              aria-hidden="true"
            />
            <span className="text-gray-500">{entry.name}:</span>
            <span className="font-medium text-gray-900">
              {formatCurrency(entry.value)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CapExLineChart({
  data,
  isLoading = false,
  className,
}: CapExLineChartProps) {
  if (isLoading) {
    return <ShimmerLoader variant="chart" className={cn("h-80", className)} />;
  }

  if (!data || data.quarters.length === 0) {
    return (
      <Card className={cn("flex min-h-64 items-center justify-center", className)}>
        <p className="text-sm text-gray-500">No data available</p>
      </Card>
    );
  }

  // Build chart-ready rows from quarters (most recent 8)
  const chartData = data.quarters.slice(-8).map((q) => ({
    period: formatDate(q.period),
    rawPeriod: q.period,
    Mining: q.mining,
    Manufacturing: q.manufacturing,
    "Other Selected": q.other_selected,
    Total: q.total,
  }));

  // Derive a trend label for aria-label
  const firstTotal = chartData[0]?.Total ?? 0;
  const lastTotal = chartData[chartData.length - 1]?.Total ?? 0;
  const trend = lastTotal >= firstTotal ? "upward" : "downward";
  const periodStart = chartData[0]?.period ?? "";
  const periodEnd = chartData[chartData.length - 1]?.period ?? "";
  const ariaLabel = `Area chart showing CapEx trends from ${periodStart} to ${periodEnd}. Total expenditure shows an ${trend} trend from ${formatCurrency(firstTotal)} to ${formatCurrency(lastTotal)}.`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0 }}
      className={className}
    >
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium tracking-tight text-gray-900">
            CapEx Trend (8 Quarters)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div
            role="img"
            aria-label={ariaLabel}
            className="h-64 w-full"
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartData}
                margin={{ top: 4, right: 8, left: 8, bottom: 4 }}
              >
                <defs>
                  <linearGradient id="totalGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0f172a" stopOpacity={0.12} />
                    <stop offset="95%" stopColor="#0f172a" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="miningGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#d97706" stopOpacity={0.08} />
                    <stop offset="95%" stopColor="#d97706" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="manufacturingGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#059669" stopOpacity={0.08} />
                    <stop offset="95%" stopColor="#059669" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="otherGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.08} />
                    <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#f1f5f9"
                  vertical={false}
                />
                <XAxis
                  dataKey="period"
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: "#e2e8f0" }}
                />
                <YAxis
                  tickFormatter={(value: number) => formatCurrency(value)}
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={72}
                />
                <Tooltip
                  content={<CustomTooltip />}
                  cursor={{ stroke: "#e2e8f0", strokeWidth: 1 }}
                />
                <Legend
                  wrapperStyle={{ fontSize: "12px", color: "#94a3b8", paddingTop: "8px" }}
                />
                <Area
                  type="monotone"
                  dataKey="Total"
                  stroke="#0f172a"
                  strokeWidth={2.5}
                  fill="url(#totalGradient)"
                  dot={false}
                  activeDot={{ r: 4, fill: "#0f172a" }}
                />
                <Area
                  type="monotone"
                  dataKey="Mining"
                  stroke="#d97706"
                  strokeWidth={1.5}
                  strokeDasharray="5 3"
                  fill="url(#miningGradient)"
                  dot={false}
                  activeDot={{ r: 3, fill: "#d97706" }}
                />
                <Area
                  type="monotone"
                  dataKey="Manufacturing"
                  stroke="#059669"
                  strokeWidth={1.5}
                  strokeDasharray="5 3"
                  fill="url(#manufacturingGradient)"
                  dot={false}
                  activeDot={{ r: 3, fill: "#059669" }}
                />
                <Area
                  type="monotone"
                  dataKey="Other Selected"
                  stroke="#7c3aed"
                  strokeWidth={1.5}
                  strokeDasharray="5 3"
                  fill="url(#otherGradient)"
                  dot={false}
                  activeDot={{ r: 3, fill: "#7c3aed" }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Accessible tabular alternative */}
          <DataTable data={data} title="CapEx Trend Data Table" className="mt-4" />
        </CardContent>
      </Card>
    </motion.div>
  );
}
