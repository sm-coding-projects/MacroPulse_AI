# Product Requirements Document (PRD)

**Product Name:** MacroPulse AI
**Version:** 1.0.0
**Last Updated:** March 2026
**Status:** Draft

---

## 1. Overview

MacroPulse AI is a containerized web application designed to ingest macroeconomic data (specifically Capital Expenditure) from the Australian Bureau of Statistics (ABS) and provide AI-generated, human-readable analysis of what that data means for specific market sectors.

---

## 2. Target Audience

Data-driven investors, financial analysts, and economics enthusiasts who want quick, actionable insights from raw government data without manually parsing spreadsheets.

---

## 3. Success Criteria

The following metrics define a successful v1.0 launch:

- **Time to Insight:** A user can go from launching the app to receiving a complete AI analysis in under 90 seconds (excluding LLM response latency from third-party providers).
- **Data Accuracy:** 100% fidelity between raw ABS source data and the values displayed in the UI — no transformation errors or data loss.
- **Deployment Reliability:** A new user can go from `git clone` to a running instance with a single `docker-compose up` command, with no manual dependency installation beyond Docker and Docker Compose.
- **Analysis Quality:** AI output references specific data points from the fetched dataset (not hallucinated figures) in at least 90% of generated analyses, as validated through manual spot-checking during QA.

---

## 4. Core Features

### 4.1 Automated Data Ingestion

Connects directly to the ABS Indicator API to fetch the latest "Private New Capital Expenditure and Expected Expenditure" data.

**ABS API Details:**

- **Endpoint:** `https://indicator.data.abs.gov.au/dataflows`
- **Target Dataflow:** Private New Capital Expenditure and Expected Expenditure (Catalogue No. 5625.0)
- **Series IDs:** All series under the CapEx dataflow, including breakdowns by industry (Mining, Manufacturing, Other Selected Industries) and by asset type (Buildings & Structures, Equipment Plant & Machinery).
- **Data Format:** SDMX-JSON (Statistical Data and Metadata eXchange).
- **Frequency:** Quarterly release cycle; the app fetches the most recent 8 quarters (2 years) to enable trend comparison.
- **Rate Limits:** The ABS public API has no documented rate limits, but the app should implement a minimum 2-second delay between consecutive requests and respect HTTP 429 responses with exponential backoff.

**Caching Strategy (SQLite):**

- Fetched data is stored locally in SQLite with a timestamp column.
- Cache is considered valid for 24 hours from the last successful fetch.
- If cache is stale, the app attempts a fresh fetch. On failure (network error, API downtime, malformed response), the app falls back to cached data and displays a banner: *"Showing cached data from [date]. Live data unavailable."*
- A manual "Refresh Data" button allows users to force a re-fetch regardless of cache age.

### 4.2 Bring Your Own Key (BYOK) AI Configuration

A settings panel allowing users to input their own LLM API Key and Base URL, supporting OpenAI-compatible endpoints (including local models via Ollama).

**Configuration Fields:**

- **LLM Base URL** (required): Text input with placeholder `https://api.openai.com/v1`. Validated on save to ensure it is a well-formed URL.
- **API Key** (required for remote endpoints, optional for local): Password-masked text input.
- **Model Name** (required): Text input with placeholder `gpt-4o`. No validation beyond non-empty.

**Storage and Persistence:**

- Settings are stored in `localStorage` to persist across browser sessions. This is a deliberate choice for v1 — there is no server-side user model, and re-entering credentials on every visit would be a significant UX friction point.
- A "Clear Settings" button wipes stored values.
- The settings panel displays a brief notice: *"Your API key is stored locally in your browser and is never sent to our servers. It is transmitted directly to the LLM endpoint you configure."*

**Validation and Error Handling:**

- On save, the app sends a lightweight test request (e.g., a simple completion with `max_tokens: 1`) to the configured endpoint.
- Success: Green checkmark, "Connection verified."
- Auth failure (401/403): Red error, "Invalid API key. Please check your credentials."
- Unreachable endpoint (timeout/DNS failure): Red error, "Could not reach the LLM endpoint. Please verify the URL."
- Other errors: Red error with the HTTP status code and a brief message.

### 4.3 AI-Driven Analysis

Generates contextual economic analysis comparing current CapEx estimates to previous quarters.

**Prompt Design:**

The system prompt instructs the LLM to act as a senior macroeconomic analyst. The user message includes:

- A structured summary of the current quarter's CapEx data (total, by industry, by asset type).
- The same breakdown for the previous quarter and the year-ago quarter.
- Percentage changes (quarter-on-quarter and year-on-year).
- The current ABS estimate number (1st, 2nd, ..., 7th) for context on revision cycles.

The LLM is instructed to produce analysis covering:

1. **Headline Summary:** One-paragraph overview of the key takeaway.
2. **Sector Breakdown:** What the data signals for Mining, Manufacturing, and Other Selected Industries.
3. **Asset Mix:** Whether businesses are investing more in equipment vs. structures, and what that implies.
4. **Forward Estimates:** Interpretation of expected expenditure figures and what they suggest about business confidence.
5. **Market Implications:** Potential impact on sectors such as construction, heavy machinery, financial services, and resources.

**Output Constraints:**

- The prompt explicitly instructs: *"Only reference data points provided in the input. Do not fabricate statistics or cite external data not included here."*
- Target output length: 400–800 words.
- Format: Markdown with headers for each section.

**Hallucination Mitigation:**

- The UI displays the raw data alongside the AI analysis so users can cross-reference claims.
- A disclaimer is shown below the analysis: *"This analysis is AI-generated based on ABS data and may contain errors. It does not constitute financial advice. Verify all figures against the source data displayed above."*

### 4.4 Modern, Polished UI

Features a high-fidelity interface with a dot-grid background, tile animations, and "shimmering" loading states for a premium feel.

**Information Architecture:**

The app consists of a single page with a collapsible sidebar and a main content area:

- **Sidebar (Left):**
  - Settings panel (LLM configuration, as described in 4.2).
  - Data status indicator (last fetched date, cache status).
  - "Analyze Latest CapEx Data" primary action button.
  - "Refresh Data" secondary action button.

- **Main Content Area:**
  - **Data Section (Top):** Two charts displayed side by side on desktop, stacked on mobile:
    - *Line chart:* Total CapEx (actual) over the last 8 quarters, with separate lines for Mining, Manufacturing, and Other.
    - *Grouped bar chart:* Current quarter vs. previous quarter by asset type (Buildings & Structures vs. Equipment).
  - **Analysis Section (Below charts):** The AI-generated markdown analysis, rendered with styled headers and paragraphs.
  - **Empty State:** Before any analysis is run, the main area displays a brief explainer: *"Connect your LLM in Settings, then click 'Analyze' to get started."*

**Loading States:**

- While data is being fetched from ABS: Skeleton shimmer on chart areas.
- While waiting for LLM response: Skeleton shimmer on the analysis section with an animated "Analyzing..." label and an estimated wait time if the request exceeds 10 seconds.
- Chart tiles animate in with a subtle fade-and-slide-up (Framer Motion, 300ms, staggered by 100ms).

---

## 5. Architecture

- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, Framer Motion.
- **Backend:** Python, FastAPI, Pandas, Requests.
- **Database:** SQLite (for local caching of ABS data).
- **Infrastructure:** Docker, `docker-compose.yml`.

**Service Topology:**

- `frontend` container: Next.js on port 3000. Proxies API calls to the backend.
- `backend` container: FastAPI on port 8000. Handles ABS data fetching, cleaning, caching, and proxying LLM requests.
- Shared volume: SQLite database file mounted into the backend container.

**API Contracts (Backend ↔ Frontend):**

- `GET /api/data/capex` — Returns the latest cached CapEx data (or triggers a fresh fetch if cache is stale). Response is a JSON object with `quarters` (array), `by_industry` (nested object), `by_asset_type` (nested object), `metadata` (source, last_updated, estimate_number).
- `POST /api/analyze` — Accepts `{ base_url, api_key, model, data_summary }` in the request body. The backend constructs the full prompt, calls the LLM, and streams the response back. Returns `{ analysis: string, tokens_used: number }`.
- `POST /api/settings/test` — Accepts `{ base_url, api_key, model }` and performs a lightweight validation request. Returns `{ success: boolean, error?: string }`.

---

## 6. User Flow

1. User launches the app via `docker-compose up` and opens `localhost:3000`.
2. The main content area shows the empty state with setup instructions.
3. User opens the sidebar and enters their LLM Base URL, API Key, and Model Name. Clicks "Save." The app validates the connection.
4. User clicks "Analyze Latest CapEx Data."
5. Backend checks cache validity. If stale, fetches fresh data from ABS (shimmer on charts). If ABS is unreachable, falls back to cached data with a warning banner.
6. Charts render with fetched data (animated tile entrance).
7. Backend constructs the analysis prompt and calls the configured LLM. The analysis section shows a shimmer loading state.
8. AI analysis streams in and renders as formatted markdown below the charts.
9. User can scroll between charts and analysis to cross-reference figures.

---

## 7. Error Handling Philosophy

The app should fail gracefully and always communicate state clearly to the user. No silent failures.

- **ABS API unavailable:** Fall back to cached data with a visible warning. If no cache exists (first run), display a clear error: *"Unable to fetch data from ABS. Please check your internet connection and try again."*
- **LLM endpoint unreachable or returns an error:** Display the error in the analysis section with a "Retry" button. Do not leave the user on a perpetual loading state — timeout after 60 seconds.
- **Malformed ABS data:** Log the raw response for debugging. Display: *"The data received from ABS was in an unexpected format. This may indicate an API change. Please report this issue."*
- **LLM returns empty or nonsensical output:** Display the raw output with a notice: *"The AI response may not have been generated correctly. Try adjusting your model or prompt settings."*

---

## 8. Data Privacy Considerations

- The user's LLM API key is stored in `localStorage` only and is never transmitted to the MacroPulse backend. It is sent directly from the frontend to the user's configured LLM endpoint via the backend proxy (the backend does not log or persist it).
- ABS data is publicly available government data and carries no privacy concerns.
- When the user triggers an analysis, the ABS data is included in the LLM prompt and sent to the user's configured third-party endpoint. The settings panel notes: *"Your economic data will be sent to the LLM endpoint you configure. If using a cloud-hosted model, review your provider's data retention policies."*
- No telemetry, analytics, or tracking is included in v1.

---

## 9. Performance Targets

- **Initial page load:** Under 2 seconds on a standard broadband connection.
- **ABS data fetch and parse:** Under 5 seconds.
- **Chart rendering:** Under 500ms after data is available.
- **LLM response:** Not directly controllable (depends on provider), but the UI must remain responsive and show progress indicators. Timeout at 60 seconds.

---

## 10. Accessibility Requirements

- All charts include `aria-label` descriptions summarizing the data trend.
- Color choices meet WCAG 2.1 AA contrast ratios (minimum 4.5:1 for text, 3:1 for large text and UI elements).
- The sidebar and all interactive elements are keyboard-navigable.
- Loading states are announced to screen readers via `aria-live` regions.
- Chart data is also available in a tabular format (collapsible table below each chart) for users who cannot interpret visual charts.

---

## 11. Testing Strategy

- **Unit Tests:** Backend data transformation functions (ABS response parsing, percentage calculations, prompt construction) tested with Pytest. Minimum 80% coverage on the `/api/` layer.
- **Integration Tests:** End-to-end test of the ABS fetch → cache → serve pipeline using a mocked ABS response fixture.
- **LLM Integration Tests:** A test suite using a mocked LLM endpoint that returns known responses, verifying the frontend correctly renders streamed markdown.
- **Manual QA:** Before release, run 10 analysis cycles with at least 2 different LLM providers (e.g., OpenAI, Ollama with Llama) and verify that generated analyses reference only data points present in the input.

---

## 12. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ABS API changes structure or endpoints | Medium | High | Pin to a specific API version. Monitor ABS release notes. Include a clear error message if the response format is unrecognised. |
| LLM hallucinates statistics | High | High | Prompt engineering to constrain output. Raw data displayed alongside analysis. Disclaimer on all AI output. |
| User enters invalid or malicious LLM endpoint | Low | Medium | URL validation on save. Test request before persisting. Backend proxy does not follow redirects beyond one hop. |
| Docker/port conflicts on user machine | Medium | Low | Document prerequisites (Docker, Docker Compose). Use configurable port via `.env` file. Document troubleshooting for port 3000 conflicts. |
| SQLite corruption or lock contention | Low | Medium | Use WAL mode for concurrent reads. Backend handles `sqlite3.OperationalError` gracefully. |
| ABS data delayed beyond expected release schedule | Medium | Low | App works with whatever data is available. No hard dependency on a specific release date. |

---

## 13. Deployment Prerequisites

Users must have the following installed before running `docker-compose up`:

- Docker Engine 20.10+ (or Docker Desktop).
- Docker Compose v2.0+.
- Ports 3000 (frontend) and 8000 (backend) available, or configured via the `.env` file.
- An active internet connection for the initial ABS data fetch and for cloud-hosted LLM endpoints. Ollama users running local models can operate offline after the first data fetch.

---

## 14. Out of Scope (For v1.0)

- User authentication/login systems.
- Cloud database integration (e.g., AWS RDS).
- Ingesting datasets other than ABS CapEx.
- Customisable prompts or analysis templates (the prompt is hardcoded in v1).
- Export functionality (PDF reports, CSV downloads).
- Multi-language support.
- Mobile-native app (the web UI is responsive but not a native app).
