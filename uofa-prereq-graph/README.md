# UofA Prereq Graph (app)

Single project folder for the course graph **web UI** and **API**. Python modules and the Vite/React app live side by side (no `frontend/` / `backend/` split).

## Structure

- `app.py`, `graph_builder.py` — FastAPI service and graph builder
- `src/` — React UI (graph canvas, search, routing)
- `tests/` — Python API/graph tests
- `package.json` — Node tooling (Vite, Vitest, ESLint)

## Environment

- **API:** `DATABASE_URL` (required)
- **API (optional):** `CORS_EXTRA_ORIGINS` — comma-separated origins for LAN or staging
- **Web:** `VITE_API_BASE_URL` — defaults to `http://localhost:8000` (set in `.env.development.local` for device testing)

Load env from the repo root `.env` or `uofa-prereq-graph/.env` via `python-dotenv` in `app.py`.

## Run locally

**API** (install Python deps from repo root, then run from this directory):

```bash
pip install -r ../requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Web:**

```bash
npm install
npm run dev -- --host
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Vite dev server |
| `npm run build` | Production build → `dist/` |
| `npm run test` | Vitest unit tests |
| `npm run lint` | ESLint |

## API endpoints

- `GET /health`
- `GET /courses`
- `GET /courses/{code}`
- `GET /graph/{code}` — query: `max_depth`, `include_coreqs`, `view` (`prereq` \| `dependency`)

## Deploy notes

- **Vercel:** set the project root directory to `uofa-prereq-graph` (includes `vercel.json`).
- **AWS Lambda:** root `template.yaml` packages this folder; copy root `requirements.txt` here before `sam build` (CI does this automatically). `.samignore` excludes Node/Vite files from the Lambda artifact.

## UI behavior

- **Prerequisite view:** depth filter, optional corequisites, AND/OR group nodes.
- **Dependency view:** one level of courses that list the root as a prerequisite.
- Graph rendering uses vis-network; see `src/components/GraphCanvas.tsx`.
