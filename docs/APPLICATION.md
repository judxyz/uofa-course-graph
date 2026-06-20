# Application — API & Web UI

Read-only app: query PostgreSQL and render prerequisite / dependency graphs. Does not scrape.

```
Browser (React) → FastAPI (Lambda/local) → PostgreSQL
     Vercel              AWS SAM
```

## Stack

| Layer | Tech | Deploy |
|-------|------|--------|
| UI | React 19, TypeScript, Vite, vis-network | Vercel (`uofa-course-graph/`) |
| API | FastAPI, psycopg, Mangum | AWS Lambda (`template.yaml`) |
| DB | PostgreSQL | Supabase |

## Structure (`uofa-course-graph/`)

| Path | Role |
|------|------|
| `app.py` | Routes, CORS, Lambda handler |
| `graph_builder.py` | DB → graph JSON |
| `src/pages/GraphPage.tsx` | Main UI |
| `src/components/GraphCanvas.tsx` | vis-network graph |
| `src/components/SearchBar.tsx` | Course search |
| `src/hooks/useCourseGraph.ts` | Fetch + view state |
| `src/api/` | HTTP wrappers |

## Environment

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | Yes (API) | Postgres connection |
| `CORS_EXTRA_ORIGINS` | No | Extra CORS origins (comma-separated) |
| `VITE_API_BASE_URL` | No | API URL for frontend (default `http://localhost:8000`) |

## Local dev

```bash
# API (from uofa-course-graph/)
pip install -r ../requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# UI
cd uofa-course-graph && npm install && npm run dev -- --host
```

Default course: **CMPUT 267** (`GET /` → `default_course`).

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/courses` | List `{ code, title }` |
| `GET` | `/courses/{code}` | Course detail + raw prereq text + `parse_status` |
| `GET` | `/graph/{code}` | Graph payload |

**`GET /graph/{code}` params:**

| Param | Default | Description |
|-------|---------|-------------|
| `max_depth` | `1` | Course levels of prereqs to expand (0–8); group nodes don't count |
| `include_coreqs` | `true` | Include corequisite branches |
| `view` | `prereq` | `prereq` (recursive tree) or `dependency` (one level: courses that require root) |

404 if course not found.

## Graph builder

`GraphBuilder` reads `courses`, `requirement_groups`, `requirement_items`, `course_edges` and returns:

- `rootCourse`, `groups`, `items`
- `nodes` — `course` | `group` | `requirement`
- `edges` — `{ source, target, relationType }` for vis-network
- `rawPrerequisiteText`, `rawCorequisiteText`, `meta`

Expansion uses `max_depth` on courses only, with cycle protection. Code lookup: uppercase, hyphen → space.

## Frontend

**Routes:** `/` and `/graph/:code` (URL uses hyphens, e.g. `CMPUT-267`).

**Features:** search (`GET /courses`), depth filter (1–4), coreq toggle, prereq vs dependency view, node click → `GET /courses/{code}` for description.

**Key modules:** `useCourseGraph` (loads graph on code/param change), `GraphCanvas` (hierarchical vis-network layout).

## Deploy

- **Frontend:** Vercel, root `uofa-course-graph`, set `VITE_API_BASE_URL` to Lambda URL.
- **API:** GitHub Actions `deploy-backend.yml` — secrets `DATABASE_URL`, `AWS_DEPLOY_ROLE_ARN`. Handler `app.handler`, Python 3.12.

## CI

| Job | Checks |
|-----|--------|
| `app` | ESLint, Vitest, Vite build |
| `api` | Python compile, handler import |
| `scraper` | `pytest` |
| `sam-build` | SAM validate + build |

## Scripts

| Command | Action |
|---------|--------|
| `npm run dev` | Vite dev server |
| `npm run build` | Production build |
| `npm run test` | Vitest |
| `npm run lint` | ESLint |
