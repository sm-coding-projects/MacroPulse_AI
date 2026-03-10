"use client";

import { LineChart, Line, ResponsiveContainer, Tooltip } from "recharts";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EconomicIndicatorsData, IndicatorPoint } from "@/lib/types";

interface EconomicIndicatorsPanelProps {
  data: EconomicIndicatorsData;
  className?: string;
}

interface IndicatorCardProps {
  title: string;
  unit: string;
  series: IndicatorPoint[];
  positiveIsGood: boolean;
}

function IndicatorCard({ title, unit, series, positiveIsGood }: IndicatorCardProps) {
  if (!series.length) return null;

  const latest = series[series.length - 1];
  const prev = series.length >= 2 ? series[series.length - 2] : null;
  const trend = prev ? latest.value - prev.value : 0;
  const isPositive = trend > 0;
  const isGood = positiveIsGood ? isPositive : !isPositive;

  const valueColor =
    trend === 0
      ? "text-gray-700"
      : isGood
      ? "text-emerald-600"
      : "text-red-600";

  const TrendIcon = trend > 0 ? TrendingUp : trend < 0 ? TrendingDown : Minus;

  const latestPeriod = latest.period;
  const latestValue = `${latest.value.toFixed(1)}${unit}`;

  return (
    <div
      className="rounded-xl border border-gray-200 bg-white p-4 flex flex-col gap-3 shadow-sm"
      role="region"
      aria-label={`${title}: ${latestValue} as of ${latestPeriod}`}
    >
      <div className="flex items-start justify-between">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
          {title}
        </span>
        <TrendIcon
          className={cn("h-3.5 w-3.5 shrink-0", valueColor)}
          aria-hidden="true"
        />
      </div>

      <div>
        <span className={cn("text-2xl font-bold tabular-nums", valueColor)}>
          {latestValue}
        </span>
        <p className="text-xs text-gray-400 mt-0.5">{latestPeriod}</p>
      </div>

      {/* Sparkline — decorative, hidden from screen readers */}
      <div className="h-12" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
            <Line
              type="monotone"
              dataKey="value"
              stroke={isGood ? "#059669" : trend === 0 ? "#94a3b8" : "#dc2626"}
              strokeWidth={1.5}
              dot={false}
            />
            <Tooltip
              contentStyle={{
                background: "#ffffff",
                border: "1px solid #e5e7eb",
                borderRadius: 6,
                fontSize: 11,
                boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
              }}
              itemStyle={{ color: "#374151" }}
              formatter={(v: number) => [`${v.toFixed(2)}${unit}`, title]}
              labelFormatter={(l: string) => l}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function EconomicIndicatorsPanel({
  data,
  className,
}: EconomicIndicatorsPanelProps) {
  return (
    <section
      className={cn("space-y-3", className)}
      aria-label="Economic context indicators"
    >
      <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
        Economic Context
      </h2>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <IndicatorCard
          title="GDP Growth"
          unit="%"
          series={data.gdp_growth}
          positiveIsGood={true}
        />
        <IndicatorCard
          title="CPI Inflation"
          unit="%"
          series={data.cpi_inflation}
          positiveIsGood={false}
        />
        <IndicatorCard
          title="Unemployment"
          unit="%"
          series={data.unemployment_rate}
          positiveIsGood={false}
        />
        <IndicatorCard
          title="Wage Growth"
          unit="%"
          series={data.wage_growth}
          positiveIsGood={true}
        />
      </div>
    </section>
  );
}
