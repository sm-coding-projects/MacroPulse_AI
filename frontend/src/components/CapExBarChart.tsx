"use client";

import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LabelList,
  ResponsiveContainer,
  Cell,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ShimmerLoader } from "@/components/ShimmerLoader";
import { DataTable } from "@/components/DataTable";
import { cn, formatCurrency, formatPercentChange } from "@/lib/utils";
import type { CapExData } from "@/lib/types";

interface CapExBarChartProps {
  data: CapExData;
  isLoading?: boolean;
  className?: string;
}

interface BarChartRow {
  group: string;
  current: number;
  previous: number;
  change: number | null;
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

interface PercentChangeLabelProps {
  x?: number | string;
  y?: number | string;
  width?: number | string;
  value?: number | null;
  index?: number;
}

function PercentChangeLabel({ x = 0, y = 0, width = 0, value }: PercentChangeLabelProps) {
  if (value === null || value === undefined) return null;
  const numX = typeof x === "string" ? parseFloat(x) : x;
  const numY = typeof y === "string" ? parseFloat(y) : y;
  const numWidth = typeof width === "string" ? parseFloat(width) : width;
  const formatted = formatPercentChange(value);
  const isPositive = value >= 0;

  return (
    <text
      x={numX + numWidth / 2}
      y={numY - 4}
      textAnchor="middle"
      fill={isPositive ? "#059669" : "#dc2626"}
      fontSize={10}
      fontWeight={500}
    >
      {formatted}
    </text>
  );
}

export function CapExBarChart({
  data,
  isLoading = false,
  className,
}: CapExBarChartProps) {
  if (isLoading) {
    return <ShimmerLoader variant="chart" className={cn("h-80", className)} />;
  }

  if (!data || data.quarters.length < 2) {
    return (
      <Card className={cn("flex min-h-64 items-center justify-center", className)}>
        <p className="text-sm text-gray-500">
          {data && data.quarters.length < 2
            ? "At least two quarters of data are required for comparison"
            : "No data available"}
        </p>
      </Card>
    );
  }

  const quarters = data.quarters;
  const current = quarters[quarters.length - 1];
  const previous = quarters[quarters.length - 2];

  const currentLabel = current.period;
  const previousLabel = previous.period;

  // Compute QoQ % change helper
  const pctChange = (curr: number, prev: number): number | null => {
    if (prev === 0) return null;
    return ((curr - prev) / Math.abs(prev)) * 100;
  };

  const chartData: BarChartRow[] = [
    {
      group: "Buildings & Structures",
      current: current.buildings_structures,
      previous: previous.buildings_structures,
      change: pctChange(current.buildings_structures, previous.buildings_structures),
    },
    {
      group: "Equipment & Machinery",
      current: current.equipment_plant_machinery,
      previous: previous.equipment_plant_machinery,
      change: pctChange(current.equipment_plant_machinery, previous.equipment_plant_machinery),
    },
    {
      group: "Total",
      current: current.total,
      previous: previous.total,
      change: pctChange(current.total, previous.total),
    },
  ];

  const ariaLabel = `Grouped bar chart comparing asset type capital expenditure for ${currentLabel} versus ${previousLabel}. Buildings & Structures: ${formatCurrency(current.buildings_structures)} vs ${formatCurrency(previous.buildings_structures)}. Equipment & Machinery: ${formatCurrency(current.equipment_plant_machinery)} vs ${formatCurrency(previous.equipment_plant_machinery)}. Total: ${formatCurrency(current.total)} vs ${formatCurrency(previous.total)}.`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className={className}
    >
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium tracking-tight text-gray-900">
            Asset Type Comparison (QoQ)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div
            role="img"
            aria-label={ariaLabel}
            className="h-64 w-full"
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 20, right: 8, left: 8, bottom: 4 }}
                barGap={4}
                barCategoryGap="30%"
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#f1f5f9"
                  vertical={false}
                />
                <XAxis
                  dataKey="group"
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
                  cursor={{ fill: "rgba(148, 163, 184, 0.08)" }}
                />
                <Legend
                  wrapperStyle={{ fontSize: "12px", color: "#94a3b8", paddingTop: "8px" }}
                />
                {/* Current quarter bars — muted teal */}
                <Bar
                  dataKey="current"
                  name={currentLabel}
                  fill="#0d9488"
                  radius={[4, 4, 0, 0]}
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`current-${index}`} fill="#0d9488" />
                  ))}
                  <LabelList
                    content={(props) => (
                      <PercentChangeLabel
                        {...props}
                        value={chartData[props.index as number]?.change ?? null}
                      />
                    )}
                  />
                </Bar>
                {/* Previous quarter bars — muted salmon */}
                <Bar
                  dataKey="previous"
                  name={previousLabel}
                  fill="#fb7185"
                  radius={[4, 4, 0, 0]}
                >
                  {chartData.map((_entry, index) => (
                    <Cell key={`previous-${index}`} fill="#fb7185" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Accessible tabular alternative */}
          <DataTable data={data} title="Asset Type Comparison Data Table" className="mt-4" />
        </CardContent>
      </Card>
    </motion.div>
  );
}
