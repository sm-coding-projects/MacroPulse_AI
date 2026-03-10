import type {
  CapExData,
  ChatMessage,
  DataResponse,
  IndicatorsResponse,
  LLMSettings,
  SettingsTestResponse,
} from "@/lib/types";

const BASE = "/api";

/**
 * Fetch the latest CapEx data from the backend cache or ABS API.
 * Pass forceRefresh=true to bypass the cache and always pull from ABS.
 * Never throws — returns a DataResponse with error field on failure.
 */
export async function fetchCapExData(forceRefresh = false): Promise<DataResponse> {
  const url = forceRefresh
    ? `${BASE}/data/capex?force_refresh=true`
    : `${BASE}/data/capex`;
  try {
    const res = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return {
        data: null,
        from_cache: false,
        cache_date: null,
        error: `Failed to fetch data (HTTP ${res.status}). ${text}`.trim(),
      };
    }

    const json: DataResponse = await res.json();
    return json;
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "An unexpected error occurred.";
    return {
      data: null,
      from_cache: false,
      cache_date: null,
      error: `Could not reach the server. ${message}`,
    };
  }
}

/**
 * Test that the provided LLM settings can connect to the configured endpoint.
 * Never throws — returns a SettingsTestResponse with error field on failure.
 */
export async function testLLMConnection(
  settings: LLMSettings
): Promise<SettingsTestResponse> {
  try {
    const res = await fetch(`${BASE}/settings/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        base_url: settings.base_url,
        api_key: settings.api_key,
        model: settings.model,
      }),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return {
        success: false,
        error: `Server returned HTTP ${res.status}. ${text}`.trim(),
      };
    }

    const json: SettingsTestResponse = await res.json();
    return json;
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "An unexpected error occurred.";
    return {
      success: false,
      error: `Could not reach the server. ${message}`,
    };
  }
}

/**
 * Fetch the latest economic indicator data (GDP, CPI, unemployment, wages).
 * Never throws — returns an IndicatorsResponse with error field on failure.
 */
export async function getEconomicIndicators(): Promise<IndicatorsResponse> {
  const res = await fetch("/api/data/indicators");
  if (!res.ok) {
    return { data: null, from_cache: false, cache_date: null, error: `HTTP ${res.status}` };
  }
  return res.json() as Promise<IndicatorsResponse>;
}

/**
 * Send a follow-up question about the analysis. Returns the raw Response
 * object so the caller can read the SSE stream via response.body.
 * Never throws — on fetch failure returns a Response with ok: false.
 */
export async function chatWithAnalysis(
  settings: LLMSettings,
  analysis: string,
  chatHistory: ChatMessage[],
  question: string,
  signal?: AbortSignal
): Promise<Response> {
  try {
    const res = await fetch(`${BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        base_url: settings.base_url,
        api_key: settings.api_key,
        model: settings.model,
        question,
        analysis,
        chat_history: chatHistory,
      }),
      signal,
    });
    return res;
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "An unexpected error occurred.";
    return new Response(
      JSON.stringify({ error: `Could not reach the server. ${message}` }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }
}

/**
 * Initiate a streaming analysis request. Returns the raw Response object so
 * the caller can read the SSE stream via response.body.
 * Never throws — on fetch failure returns a Response with ok: false.
 */
export async function analyzeCapEx(
  settings: LLMSettings,
  data: CapExData,
  signal?: AbortSignal
): Promise<Response> {
  try {
    const body = JSON.stringify({
      base_url: settings.base_url,
      api_key: settings.api_key,
      model: settings.model,
      data_summary: {
        quarters: data.quarters,
        metadata: data.metadata,
      },
    });

    const res = await fetch(`${BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      signal,
    });

    return res;
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "An unexpected error occurred.";
    return new Response(
      JSON.stringify({ error: `Could not reach the server. ${message}` }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }
}
