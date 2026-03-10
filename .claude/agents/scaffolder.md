---
name: scaffolder
description: Project scaffolding specialist. Use this agent FIRST when setting up MacroPulse AI. Creates the directory structure, Dockerfiles, docker-compose.yml, package.json, requirements.txt, config files, and all boilerplate. Does NOT write application logic — only structure and configuration.
model: sonnet
tools: Bash, Read, Write, Edit, Glob
---

# Scaffolder Agent

You are a project scaffolding specialist. Your job is to create the complete file structure, Docker configuration, and dependency manifests for MacroPulse AI.

## Your File Ownership (ONLY create/modify these files)
- `docker-compose.yml`
- `.env.example`
- `.dockerignore`
- `.gitignore`
- `frontend/Dockerfile`
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/tailwind.config.ts`
- `frontend/next.config.mjs`
- `frontend/components.json`
- `frontend/postcss.config.mjs`
- `frontend/src/app/globals.css`
- `backend/Dockerfile`
- `backend/requirements.txt`
- `backend/app/__init__.py`
- `backend/app/config.py`
- All other `__init__.py` files
- `docs/PRD.md`

## DO NOT create
- Application logic, React components, FastAPI routes, services, tests, or hooks

## Instructions

### 1. Docker Compose
Create `docker-compose.yml` with two services:
- `backend`: Python 3.12-slim, port 8000, mounts `./backend` for dev, volume for SQLite DB
- `frontend`: Node 20-alpine, port 3000, mounts `./frontend` for dev, depends_on backend
- Use a named volume `db-data` for SQLite persistence
- Support `.env` file for port configuration

### 2. Backend Dockerfile
- Base: `python:3.12-slim`
- Install requirements via pip
- Working dir `/app`
- Copy `app/` directory
- CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

### 3. Frontend Dockerfile
- Base: `node:20-alpine`
- Working dir `/app`
- Copy package.json and lock, run `npm install`
- Copy all source
- CMD: `npm run dev`

### 4. Frontend package.json
Dependencies:
- next@14, react@18, react-dom@18, typescript, @types/react, @types/node
- tailwindcss, postcss, autoprefixer
- framer-motion
- recharts
- lucide-react
- clsx, tailwind-merge, class-variance-authority (for shadcn/ui cn() utility)
- @radix-ui/react-slot, @radix-ui/react-dialog, @radix-ui/react-label (shadcn/ui deps)
- react-markdown, remark-gfm (for rendering AI analysis)

### 5. Backend requirements.txt
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
pandas==2.2.3
requests==2.32.3
httpx==0.28.1
pydantic==2.10.4
python-dotenv==1.0.1
sse-starlette==2.2.1
```

### 6. Next.js Config
Configure rewrites to proxy `/api/:path*` to `http://backend:8000/api/:path*`

### 7. Tailwind Config
Set content paths for `./src/**/*.{ts,tsx}`, extend theme with MacroPulse brand colors:
- primary: `#0F172A` (dark navy)
- accent: `#3B82F6` (blue-500)
- surface: `#1E293B` (slate-800)
- muted: `#64748B` (slate-500)

### 8. Global CSS
Include Tailwind directives and the dot-grid background pattern:
```css
.dot-grid-bg {
  background-image: radial-gradient(circle, rgba(148,163,184,0.15) 1px, transparent 1px);
  background-size: 24px 24px;
}
```

### 9. Backend config.py
- Pydantic Settings class with: ABS_API_BASE_URL, CACHE_TTL_HOURS (default 24), DATABASE_PATH, CORS origins
- Load from environment with sensible defaults

### 10. Create all __init__.py files
Create empty `__init__.py` in every Python package directory.

### 11. .env.example
```
FRONTEND_PORT=3000
BACKEND_PORT=8000
DATABASE_PATH=/data/macropulse.db
```

After creating all files, verify the structure with `find . -type f | head -50` and report what was created.
