# MacroPulse AI

## Project Overview
MacroPulse AI is a containerized web app that ingests Australian Bureau of Statistics (ABS) Capital Expenditure data and provides AI-generated economic analysis. Users bring their own LLM API key (OpenAI-compatible endpoints, including Ollama).

## Architecture
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Framer Motion, Recharts
- **Backend:** Python 3.12, FastAPI, Pandas, Requests, SQLite (WAL mode)
- **Infrastructure:** Docker Compose with two services (`frontend` on port 3000, `backend` on port 8000)

## Directory Structure
```
macropulse-ai/
├── CLAUDE.md
├── docker-compose.yml
├── .env.example
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.mjs
│   ├── components.json          # shadcn/ui config
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── ui/              # shadcn/ui primitives
│   │   │   ├── Sidebar.tsx
│   │   │   ├── SettingsPanel.tsx
│   │   │   ├── CapExLineChart.tsx
│   │   │   ├── CapExBarChart.tsx
│   │   │   ├── AnalysisDisplay.tsx
│   │   │   ├── DataStatusBadge.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   └── ShimmerLoader.tsx
│   │   ├── lib/
│   │   │   ├── api.ts           # Backend API client
│   │   │   ├── types.ts         # Shared TypeScript types
│   │   │   └── utils.ts         # cn() helper, formatters
│   │   └── hooks/
│   │       ├── useSettings.ts   # localStorage LLM config
│   │       └── useCapExData.ts  # Data fetching hook
│   └── public/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, CORS, lifespan
│   │   ├── config.py            # Settings, constants
│   │   ├── database.py          # SQLite setup, WAL mode
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── data.py          # GET /api/data/capex
│   │   │   └── analyze.py       # POST /api/analyze, POST /api/settings/test
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── abs_client.py    # ABS API integration
│   │   │   ├── data_processor.py # Pandas transformations
│   │   │   ├── cache.py         # SQLite cache logic
│   │   │   └── llm_proxy.py     # LLM proxy with streaming
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py       # Pydantic request/response models
│   │   └── prompts/
│   │       ├── __init__.py
│   │       └── analysis.py      # System + user prompt templates
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_abs_client.py
│       ├── test_data_processor.py
│       ├── test_cache.py
│       └── test_routers.py
└── docs/
    └── PRD.md
```

## Coding Standards
- Python: type hints on all functions, docstrings on public functions, Black formatting, isort imports
- TypeScript: strict mode, no `any` types, prefer interfaces over type aliases for objects
- All API responses use Pydantic models (backend) and TypeScript interfaces (frontend)
- Error messages are user-facing — write them clearly, never expose stack traces
- Environment variables via `.env` file, never hardcode secrets
- Git commits: conventional commits format (`feat:`, `fix:`, `chore:`, `test:`, `docs:`)

## Key Technical Decisions
- SQLite in WAL mode for concurrent reads without locking
- Frontend proxies `/api/*` to backend via Next.js rewrites (not direct CORS)
- LLM API key stored in localStorage, sent to backend per-request, never persisted server-side
- ABS data cached for 24 hours with fallback to stale cache on API failure
- LLM responses streamed via Server-Sent Events through the backend proxy

## Important Constraints
- The ABS Indicator API returns SDMX-JSON format — parse carefully
- All AI-generated analysis must display alongside raw data so users can cross-reference
- Every chart must have an accessible tabular alternative (collapsible table)
- WCAG 2.1 AA contrast ratios required (4.5:1 for text, 3:1 for UI elements)
- Docker containers must work on both ARM64 (Apple Silicon) and AMD64

## Agent Delegation Rules
When building this project, delegate tasks to the specialized subagents defined in `.claude/agents/`. Each agent owns specific files — respect file ownership to avoid context bloat. Build in this order:
1. Use `scaffolder` agent first to create project structure and Docker configs
2. Use `backend-builder` agent for all Python/FastAPI code
3. Use `frontend-shell` agent for Next.js setup, layout, sidebar, settings
4. Use `frontend-viz` agent for charts, analysis display, animations
5. Use `test-writer` agent to create test suites
6. Use `code-reviewer` agent for a final read-only review pass

## Skills
- Read `.claude/skills/abs-api/SKILL.md` before writing any ABS API integration code
- Read `.claude/skills/project-conventions/SKILL.md` for coding patterns and style rules
