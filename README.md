# MacroPulse AI — Claude Code Agent Build System

This repository contains the complete scaffolding for building MacroPulse AI using Claude Code's subagent delegation system. A single prompt orchestrates 6 specialized agents to build the entire application.

## What's Included

```
macropulse-ai/
├── CLAUDE.md                              # Project context (loaded every session)
├── PROMPT.md                              # ← THE MASTER PROMPT (copy into Claude Code)
├── docs/
│   └── PRD.md                             # Full product requirements document
├── .claude/
│   ├── settings.json                      # Claude Code settings (enables agent teams)
│   ├── agents/                            # 6 specialized subagents
│   │   ├── scaffolder.md                  # Project structure, Docker, configs
│   │   ├── backend-builder.md             # FastAPI, ABS client, LLM proxy, all services
│   │   ├── frontend-shell.md              # Next.js layout, sidebar, settings, hooks, types
│   │   ├── frontend-viz.md                # Recharts charts, analysis display, animations
│   │   ├── test-writer.md                 # Pytest test suite with fixtures and mocks
│   │   └── code-reviewer.md               # Read-only review (security, a11y, types, errors)
│   └── skills/                            # Domain knowledge loaded on demand
│       ├── abs-api/
│       │   └── SKILL.md                   # ABS Indicator API reference + SDMX-JSON parsing
│       └── project-conventions/
│           └── SKILL.md                   # Coding patterns, naming, error handling style
```

## Agent Architecture

```
┌─────────────────────────────────────────────────┐
│              YOU (Team Lead / Orchestrator)       │
│              Runs the master prompt               │
└──────────┬──────────┬──────────┬────────────────┘
           │          │          │
     Phase 1    Phase 2    Phase 3-4    Phase 5    Phase 6
       │          │          │            │          │
  ┌────▼───┐ ┌───▼────┐ ┌──▼───────┐ ┌──▼────┐ ┌──▼──────┐
  │Scaffold│ │Backend │ │Frontend  │ │Test   │ │Code     │
  │  er    │ │Builder │ │Shell+Viz │ │Writer │ │Reviewer │
  └────────┘ └────────┘ └──────────┘ └───────┘ └─────────┘
   Docker     FastAPI     Next.js      Pytest    Read-only
   Configs    Services    Components   Suites    Audit
              Routes      Hooks
              Models      Charts
```

All agents use `model: sonnet` (Sonnet 4.6) for cost efficiency.

## How to Use

### 1. Install Claude Code
```bash
# If not already installed
npm install -g @anthropic/claude-code
```

### 2. Clone / Set Up This Repo
```bash
cd macropulse-ai
```

### 3. Enable Agent Teams (optional, for future use)
The `.claude/settings.json` already enables experimental agent teams. Subagents work without this flag, but if you want to try the full Agent Teams feature later, it's ready.

### 4. Launch Claude Code
```bash
claude
```

### 5. Paste the Master Prompt
Open `PROMPT.md`, copy everything below the `---` separator in the "The Prompt" section, and paste it into Claude Code. Claude will:

1. **Phase 1:** Delegate to `scaffolder` → creates all project structure and Docker configs
2. **Phase 2:** Delegate to `backend-builder` → builds entire FastAPI backend
3. **Phase 3:** Delegate to `frontend-shell` → builds Next.js app shell, UI, hooks
4. **Phase 4:** Delegate to `frontend-viz` → builds charts, analysis display
5. **Phase 5:** Delegate to `test-writer` → creates comprehensive test suite
6. **Phase 6:** Delegate to `code-reviewer` → read-only audit of everything
7. **Phase 7:** Fixes any critical issues from the review

### 6. Run the App
After Claude finishes:
```bash
docker-compose up
```
Open `http://localhost:3000`

## Model Selection Note

All agents are configured with `model: sonnet` (Sonnet 4.6). This is a deliberate choice for:
- **Cost efficiency:** Sonnet is significantly cheaper per token than Opus
- **Speed:** Faster response times per agent
- **Capability:** Sonnet 4.6 is more than capable for implementation tasks

If you want to use Opus 4.6 for any agent (e.g., the code reviewer), edit the `model:` field in the relevant `.claude/agents/*.md` file.

**Note on Agent Teams:** The full Agent Teams feature (peer-to-peer messaging, shared task lists) requires Opus 4.6 as of March 2026. The subagent approach used here works with any model and achieves similar parallel delegation without the coordination overhead.

## Customization

### Adding a New Agent
Create a new file in `.claude/agents/`:
```markdown
---
name: my-agent
description: What this agent does and when to invoke it
model: sonnet
tools: Bash, Read, Write, Edit
---

Your agent's system prompt and instructions here.
```

### Adding a New Skill
Create a folder in `.claude/skills/` with a `SKILL.md`:
```markdown
---
name: my-skill
description: When to use this skill
---

Reference documentation and instructions here.
```

### Modifying the Build
Edit `PROMPT.md` to add/remove phases or change the build order. Each phase is independent — you can re-run individual phases by pasting just that section.
