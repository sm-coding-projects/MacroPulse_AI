// TypeScript interfaces mirroring backend Pydantic models exactly.

export interface CapExQuarter {
  period: string;
  total: number;
  mining: number;
  manufacturing: number;
  other_selected: number;
  buildings_structures: number;
  equipment_plant_machinery: number;
  qoq_change: number | null;
  yoy_change: number | null;
}

export interface CapExMetadata {
  source: string;
  last_updated: string;
  estimate_number: string | null;
  is_cached: boolean;
}

// Series point used in by_industry / by_asset_type chart data
export interface SeriesDataPoint {
  period: string;
  value: number;
}

export interface IndustrySeriesData {
  mining: SeriesDataPoint[];
  manufacturing: SeriesDataPoint[];
  other_selected: SeriesDataPoint[];
}

export interface AssetTypeSeriesData {
  buildings_structures: SeriesDataPoint[];
  equipment_plant_machinery: SeriesDataPoint[];
}

export interface CapExData {
  quarters: CapExQuarter[];
  by_industry: Record<string, SeriesDataPoint[]>;
  by_asset_type: Record<string, SeriesDataPoint[]>;
  metadata: Record<string, unknown>;
}

export interface LLMSettings {
  base_url: string;
  api_key: string;
  model: string;
}

export interface AnalyzeRequest {
  base_url: string;
  api_key: string;
  model: string;
  data_summary: Record<string, unknown>;
}

export interface SettingsTestResponse {
  success: boolean;
  error: string | null;
}

export interface DataResponse {
  data: CapExData | null;
  from_cache: boolean;
  cache_date: string | null;
  error: string | null;
}

export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface IndicatorPoint {
  period: string;
  value: number;
}

export interface EconomicIndicatorsData {
  gdp_growth: IndicatorPoint[];
  cpi_inflation: IndicatorPoint[];
  unemployment_rate: IndicatorPoint[];
  wage_growth: IndicatorPoint[];
  metadata: Record<string, unknown>;
}

export interface IndicatorsResponse {
  data: EconomicIndicatorsData | null;
  from_cache: boolean;
  cache_date: string | null;
  error: string | null;
}
