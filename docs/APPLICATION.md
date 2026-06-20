# Application — API & Web UI

Application queries PostgreSQL and render prerequisite / dependency graphs.

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
