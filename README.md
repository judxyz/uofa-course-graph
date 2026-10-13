## UofA Course Graph

UofA Course Graph was built as a tool for the University of Alberta, to help with looking up courses and finding their prerequisites. It also displays what courses would depend on having taken the searched course already, this can be helpful in determining the best order to take your courses in to fulfill all prerequisites.

## Tech Stack

- **App:** React, TypeScript, Vite, vis-network, FastAPI, psycopg
- **Database:** PostgreSQL (Supabase)
- **Deployment:** Vercel (frontend/web), AWS Lambda via SAM (backend/API)

## Documentation

[Data pipeline](docs/DATA_PIPELINE.md)

[Application](docs/APPLICATION.md).

## Local development

### Python Venv

1. Create and activate a venv at repo root
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### API/backend
3. Need to set `DATABASE_URL=postgresql://...` in a repo-root `.env`
4. Start the API:
   ```bash
   cd uofa-course-graph
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

To test on phone on the same Wi‑Fi, set `VITE_API_BASE_URL=http://YOUR_PC_LAN_IP:8000` in `uofa-course-graph/.env.development.local` and add `CORS_EXTRA_ORIGINS=http://YOUR_PC_LAN_IP:5173` for the API.

### Scraper (manual)

```bash
python d_run_scrape_add.py # scrape and adds to db (as set in env)
# OR
python b_scraper.py # this just scrapes the course data to data_courses.json, does not add to db
python e_parse_requirements # using the courses table, parses ALL courses in the db

```

## API overview

- `GET /health` — health check
- `GET /courses` — list course codes and titles
- `GET /courses/{code}` — one course record
- `GET /graph/{code}` — graph payload (`max_depth`, `include_coreqs`, `view=prereq|dependency`)
