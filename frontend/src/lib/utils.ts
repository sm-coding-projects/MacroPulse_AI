import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
  // ABS CapEx values are denominated in $millions
  const absVal = Math.abs(value);
  if (absVal >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}B`;
  }
  return `$${value.toFixed(1)}M`;
}

export function formatPercentChange(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function formatDate(dateStr: string): string {
  // Converts "2024-Q3" to "Sep 2024"
  const match = dateStr.match(/^(\d{4})-Q(\d)$/);
  if (!match) {
    return dateStr;
  }
  const year = match[1];
  const quarter = parseInt(match[2], 10);
  const quarterMonths: Record<number, string> = {
    1: "Mar",
    2: "Jun",
    3: "Sep",
    4: "Dec",
  };
  const month = quarterMonths[quarter] ?? "";
  return `${month} ${year}`;
}
