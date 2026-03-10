# MacroPulse AI

A containerised web app that fetches live Australian Bureau of Statistics (ABS) Capital Expenditure data and provides AI-generated economic analysis. ABS data loads automatically — no API key required. Bring your own LLM key for the analysis feature.

**Stack:** Next.js 14 · FastAPI · SQLite · Docker Compose

---

## Quick Start

**Requirement:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
git clone https://github.com/sm-coding-projects/MacroPulse_AI.git
cd MacroPulse_AI
cp .env.example .env
docker compose up --build
```

Open **http://localhost:3000**

That's it. ABS CapEx data is fetched automatically from the public ABS API on first load and cached for 24 hours.

---

## AI Analysis (optional)

To enable the AI-generated economic analysis, open **Settings** in the sidebar and enter your LLM details:

| Field | Example |
|-------|---------|
| API Base URL | `https://api.openai.com/v1` |
| API Key | Your OpenAI / Anthropic / other key |
| Model | `gpt-4o`, `claude-opus-4-6`, `llama3`, etc. |

Any OpenAI-compatible endpoint works, including local models via [Ollama](https://ollama.com) (`http://host.docker.internal:11434/v1`).

Your API key is stored only in your browser and is never persisted on the server.

---

## Stopping & Data

```bash
# Stop containers
docker compose down

# Stop and delete all cached data
docker compose down -v
```

ABS data is cached in a Docker volume (`db-data`) and survives restarts.

---

## Configuration

All config lives in `.env` (copied from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `FRONTEND_PORT` | `3000` | Port for the web UI |
| `BACKEND_PORT` | `8000` | Port for the FastAPI backend |
| `DATABASE_PATH` | `/data/macropulse.db` | SQLite database path inside the container |

---

## Architecture

```
┌─────────────────────────────┐      ┌──────────────────────────────┐
│  Frontend (Next.js / :3000) │ ───► │  Backend (FastAPI / :8000)   │
│                             │      │                              │
│  · Recharts line + bar      │      │  · ABS SDMX-JSON client      │
│  · AI analysis display      │      │  · Pandas data processing    │
│  · shadcn/ui components     │      │  · SQLite 24-hr cache        │
│  · Framer Motion animations │      │  · LLM proxy (SSE streaming) │
└─────────────────────────────┘      └──────────────────────────────┘
                                                  │
                                     ┌────────────▼─────────────┐
                                     │  ABS Indicator API       │
                                     │  (api.data.abs.gov.au)   │
                                     │  Catalogue No. 5625.0    │
                                     └──────────────────────────┘
```

---

## Development

The backend mounts the source directory as a volume, so edits to `backend/app/` apply immediately without rebuilding.

Frontend changes require a rebuild:

```bash
docker compose up --build frontend
```

Run backend tests:

```bash
docker exec macropulse-ai-backend-1 python -m pytest backend/tests/ -v
```

---

## Project Structure

```
MacroPulse_AI/
├── docker-compose.yml
├── .env.example
├── frontend/
│   ├── Dockerfile
│   └── src/
│       ├── app/              # Next.js App Router pages
│       ├── components/       # UI components + charts
│       ├── hooks/            # useCapExData, useSettings
│       └── lib/              # API client, types, utils
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── routers/          # /api/data/capex, /api/analyze
        ├── services/         # ABS client, data processor, LLM proxy, cache
        ├── models/           # Pydantic schemas
        └── prompts/          # LLM prompt templates
```

---

## Built With Claude Code

This project was built using [Claude Code](https://claude.ai/claude-code) and its subagent delegation system. A single orchestration prompt delegated work across 6 specialised agents (scaffolder, backend-builder, frontend-shell, frontend-viz, test-writer, code-reviewer) running in parallel.
