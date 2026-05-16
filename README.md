## UofA Prereq Graph

Interactive prerequisite and dependency graph explorer for University of Alberta courses.

## Repository layout

| Path | Purpose |
|------|---------|
| `uofa-prereq-graph/` | Web app (React + Vite) and API (FastAPI) in one project |
| `scraper/` | Catalogue scraper, JSON export, and database import scripts |
| `template.yaml` | AWS SAM template for API deployment |

The graph app keeps Python and TypeScript together under `uofa-prereq-graph/` (not separate `frontend/` / `backend/` folders). The scraper lives separately because it is an offline data pipeline.

## Stack

- **App:** React, TypeScript, Vite, vis-network, FastAPI, psycopg
- **Data:** Parsed UAlberta course catalogue in PostgreSQL (Supabase)
- **Deploy:** Vercel (web), AWS Lambda via SAM (API)

See `uofa-prereq-graph/README.md` and `scraper/README.md` for details.

## Local development

### Python (API + scraper)

1. Create and activate a Python virtual environment at the repo root.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   For tests: `pip install -r requirements-dev.txt`

### API
3. Set `DATABASE_URL=postgresql://...` (e.g. in a repo-root `.env`).
4. Start the API (LAN-friendly for phone testing):
   ```bash
   cd uofa-prereq-graph
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

### Web UI

1. Install dependencies:
   ```bash
   cd uofa-prereq-graph
   npm install
   ```
2. Start the dev server:
   ```bash
   npm run dev -- --host
   ```
3. Open `http://localhost:5173` (or your machine’s LAN IP on port 5173).

For a phone on the same Wi‑Fi, set `VITE_API_BASE_URL=http://YOUR_PC_LAN_IP:8000` in `uofa-prereq-graph/.env.development.local` and add `CORS_EXTRA_ORIGINS=http://YOUR_PC_LAN_IP:5173` for the API. See the app README for more.

### Scraper (optional)

From `scraper/` (after installing root `requirements.txt`):

```bash
python scraper.py              # write data/data_courses.json
python add_to_db.py            # load JSON into DATABASE_URL
# or
python run_scrape_add.py       # scrape + load in one step
```

## API overview

- `GET /health` — health check
- `GET /courses` — list course codes and titles
- `GET /courses/{code}` — one course record
- `GET /graph/{code}` — graph payload (`max_depth`, `include_coreqs`, `view=prereq|dependency`)
