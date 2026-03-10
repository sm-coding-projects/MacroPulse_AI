# MacroPulse AI — Master Build Prompt

Copy and paste this entire prompt into Claude Code to build the full application.

---

## Prerequisites

Before running, ensure:
1. You have Claude Code installed and updated
2. You are in the `macropulse-ai/` project root directory
3. The `.claude/agents/`, `.claude/skills/`, and `CLAUDE.md` files are in place

## The Prompt

Paste everything below the line into Claude Code:

---

Build the complete MacroPulse AI application from scratch by delegating to the specialized subagents defined in `.claude/agents/`. Use model sonnet for all subagents. Follow the CLAUDE.md for project context and conventions.

**IMPORTANT: Build in this exact sequence. Each phase must complete before the next begins. Do NOT attempt to write code yourself — delegate every implementation task to the appropriate subagent.**

## Phase 1: Scaffolding
Delegate to the `scaffolder` agent:
- Create the full directory structure as specified in CLAUDE.md
- Create all Dockerfiles, docker-compose.yml, package.json, requirements.txt
- Create all configuration files (tsconfig, tailwind config, next config, postcss config)
- Create globals.css with Tailwind directives and dot-grid background
- Create backend config.py with Pydantic Settings
- Create all __init__.py files
- Create .env.example, .gitignore, .dockerignore
- Copy the PRD into docs/PRD.md

Verify: The scaffolder should report the created file tree.

## Phase 2: Backend
Delegate to the `backend-builder` agent:
- First read the `.claude/skills/abs-api/SKILL.md` skill for ABS API reference
- First read the `.claude/skills/project-conventions/SKILL.md` skill for coding patterns
- Build in the order specified in the agent instructions:
  1. database.py (SQLite WAL setup)
  2. models/schemas.py (all Pydantic models)
  3. services/abs_client.py (ABS API integration)
  4. services/data_processor.py (Pandas transformations)
  5. services/cache.py (SQLite cache logic)
  6. services/llm_proxy.py (LLM proxy with streaming)
  7. prompts/analysis.py (system prompt and prompt builder)
  8. routers/data.py (GET /api/data/capex)
  9. routers/analyze.py (POST /api/analyze, POST /api/settings/test)
  10. main.py (FastAPI app with lifespan, CORS, routers)

Verify: After completion, run `cd backend && python -c "from app.main import app; print('Backend imports OK')"` to validate imports.

## Phase 3: Frontend Shell
Delegate to the `frontend-shell` agent:
- First read the `.claude/skills/project-conventions/SKILL.md` skill
- Build in the order specified in the agent instructions:
  1. lib/utils.ts (cn helper, formatters)
  2. lib/types.ts (TypeScript interfaces matching backend models)
  3. lib/api.ts (API client functions)
  4. hooks/useSettings.ts (localStorage LLM config)
  5. hooks/useCapExData.ts (data fetching hook)
  6. All shadcn/ui components (button, input, label, card, badge, sheet)
  7. ShimmerLoader.tsx
  8. DataStatusBadge.tsx
  9. EmptyState.tsx
  10. SettingsPanel.tsx
  11. Sidebar.tsx
  12. layout.tsx
  13. page.tsx (with import placeholders for chart components)

Verify: After completion, run `cd frontend && npx tsc --noEmit 2>&1 | head -20` to check for type errors.

## Phase 4: Frontend Visualizations
Delegate to the `frontend-viz` agent:
- Read the types and utils files created by frontend-shell first
- Build in order:
  1. CapExLineChart.tsx (multi-line Recharts chart)
  2. CapExBarChart.tsx (grouped bar chart)
  3. DataTable.tsx (accessible tabular data)
  4. AnalysisDisplay.tsx (markdown rendering with streaming)

After the viz agent finishes, update `frontend/src/app/page.tsx` yourself (or delegate back to frontend-shell) to replace any placeholder imports with the actual chart and analysis components.

Verify: Run `cd frontend && npx tsc --noEmit 2>&1 | head -20` again.

## Phase 5: Testing
Delegate to the `test-writer` agent:
- Read all backend source files first to understand what to test
- Build in order:
  1. conftest.py (fixtures with realistic data)
  2. test_abs_client.py
  3. test_data_processor.py
  4. test_cache.py
  5. test_routers.py

Verify: Run `cd backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -30` and report results.

## Phase 6: Code Review
Delegate to the `code-reviewer` agent:
- Review ALL files in the project
- Produce a prioritized report (Critical / Warning / Suggestion)
- Report the overall assessment

## Phase 7: Fix Issues
Based on the code reviewer's report, fix any CRITICAL issues:
- Delegate backend fixes to `backend-builder`
- Delegate frontend fixes to `frontend-shell` or `frontend-viz` as appropriate
- Re-run tests after fixes

## Final Verification
After all phases:
1. Run `cd backend && python -m pytest tests/ -v` — all tests should pass
2. Run `cd frontend && npx tsc --noEmit` — no type errors
3. Run `docker-compose config` — valid compose file
4. Report a summary of what was built: file count, test count, and any remaining warnings from the review

**Remember: You are the orchestrator. Delegate all implementation to subagents. Keep your own context focused on coordination and verification.**
