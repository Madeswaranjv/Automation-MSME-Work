# Repository Guidelines

## Project Structure & Module Organization
`backend/` contains the FastAPI service, SQLite models, watchers, scheduler, WebSocket manager, and agent orchestration code. Keep core infrastructure in `backend/core/` and agent-specific logic in `backend/agents/`. Runtime data such as `msme.db`, `chroma_db/`, and `watched_files/` also live under `backend/`.

`frontend/Web-dashboard/` is the React + TypeScript + Vite UI. Reusable UI lives in `src/components/`, route pages in `src/pages/`, and mock data in `src/data/`. Other top-level folders (`database/`, `integrations/`, `docker/`, `shared/`, `scripts/`) are reserved for cross-service assets and future tooling. `tests/` exists at repo root but is currently empty.

## Build, Test, and Development Commands
- `cd backend && python -m uvicorn main:app --reload` runs the backend locally.
- `cd backend && python -c "from main import app; print(app.title)"` is a minimal backend import smoke test.
- `cd frontend/Web-dashboard && npm run dev` starts the Vite dev server.
- `cd frontend/Web-dashboard && npm run build` performs a production build.
- `cd frontend/Web-dashboard && npm run lint` runs the configured ESLint rules.

## Coding Style & Naming Conventions
Python follows PEP 8 with 4-space indentation, type hints, and short docstrings on public functions. Prefer `snake_case` for functions/modules, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants. Use `datetime.utcnow()` consistently and load secrets from `backend/.env`, never inline them.

Frontend code follows the existing TypeScript/React style: functional components, `PascalCase` component names, `camelCase` helpers, and no semicolons. Keep files near their domain (`components/dashboard/`, `components/landing/`).

## Testing Guidelines
There is no committed backend test suite yet. For backend changes, add focused tests under `tests/` when possible and always run at least an import smoke test against `backend/main.py`. For frontend changes, run `npm run lint` and `npm run build`. Name new Python tests `test_<feature>.py` and frontend tests `*.test.ts(x)`.

## Commit & Pull Request Guidelines
Git history is currently sparse and uses short descriptive subjects such as `Frontend alone for Prototyping`. Prefer concise imperative commit messages, for example `Add HITL timeout sweep`. PRs should include a clear scope summary, affected paths, manual test steps, linked issue/task IDs, and screenshots for UI changes.

## Security & Configuration Tips
Do not commit `.env`, database dumps, or generated files from `backend/chroma_db/`. Treat `backend/core/` as infrastructure-sensitive; avoid changing it casually and keep agent work isolated to `backend/agents/` when possible.
