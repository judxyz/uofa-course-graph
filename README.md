## UofA Course Graph

Interactive prerequisite and dependency graph explorer for any course at the University of Alberta.
uofa-course-graph.vercel.app

## Stack

- **App:** React, TypeScript, Vite, vis-network, FastAPI, psycopg
- **Data:** PostgreSQL (Supabase)
- **Deploy:** Vercel (web), AWS Lambda via SAM (API)

## Documentation

Technical docs: [docs/](docs/) — [data pipeline](docs/DATA_PIPELINE.md) and [application](docs/APPLICATION.md).

## Local development

### Python

1. Create and activate a Python virtual environment at the repo root.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### API
3. Set `DATABASE_URL=postgresql://...` in a repo-root `.env`
4. Start the API:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

### Web UI

1. Install dependencies:
   ```bash
   cd uofa-course-graph
   npm install
   ```
2. Start the dev server:
   ```bash
   npm run dev -- --host
   ```
3. Open `http://localhost:5173`

For a phone on the same Wi‑Fi, set `VITE_API_BASE_URL=http://YOUR_PC_LAN_IP:8000` in `uofa-course-graph/.env.development.local` and add `CORS_EXTRA_ORIGINS=http://YOUR_PC_LAN_IP:5173` for the API. See the app README for more.

### Scraper 

```bash
python run_scrape_add.py       # scrape + load in one step
```

## API overview

- `GET /health` — health check
- `GET /courses` — list course codes and titles
- `GET /courses/{code}` — one course record
- `GET /graph/{code}` — graph payload (`max_depth`, `include_coreqs`, `view=prereq|dependency`)
