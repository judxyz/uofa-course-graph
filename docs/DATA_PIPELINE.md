# Data Pipeline — Scraping & Parsing

Offline pipeline: scrape the UAlberta course catalogue → JSON → PostgreSQL → parse prerequisites into a graph schema. **Manually triggered** (no scheduled runs or monitoring).

## Flow

```
Catalogue HTML → scraper.py → data/data_courses.json → add_to_db.py → courses
                                                              ↓
                                                   parse_requirements.py
                                                              ↓
                              requirement_groups | requirement_items | course_edges
```

## Setup

```bash
pip install -r requirements.txt
# DATABASE_URL in repo-root .env
```

| Command | Action |
|---------|--------|
| `python scraper/scraper.py` | Scrape only → `scraper/data/data_courses.json` |
| `python scraper/add_to_db.py` | Load JSON → DB |
| `python scraper/run_scrape_add.py` | Scrape + load |
| `python scraper/parse_requirements.py` | Parse all courses in DB |
| `cd scraper && pytest` | Parser unit tests |

## Modules

| File | Role |
|------|------|
| `scraper.py` | Fetch subjects, parse HTML, write JSON |
| `scrape_catalog_subjects.py` | Discover subject slugs from catalogue index |
| `add_to_db.py` | Upsert JSON into `courses` |
| `run_scrape_add.py` | Scrape + upsert in one step |
| `parse_requirements.py` | Raw text → groups, items, edges |

## Stage 1: Scrape (`scraper.py`)

**Source:** `https://apps.ualberta.ca/catalogue/course/{slug}`

**`RawCourse` fields:** `code`, `subject`, `number`, `title`, `units`, `description`, `raw_prereq_text`, `raw_coreq_text`, `catalog_url`

**Skipped entries:** unparseable heading, missing/zero units, empty description, letter-suffixed codes (e.g. `499B`), duplicate codes, prereq/coreq without a university course-code pattern.

**Prereq/coreq extraction:** regex on `Prerequisite:` / `Corequisite:` labels; strips “permission of the Department”; ignores high-school / standing-only text.

**Output:** `scraper/data/data_courses.json` (JSON array).

**Errors:** subject index failure → hardcoded `FALLBACK_CATALOG_SUBJECTS`; per-subject HTTP failure → skip and continue. No retries.

## Stage 2: Load (`add_to_db.py`)

Upserts into `courses` on `code` (`ON CONFLICT DO UPDATE`). New rows get `parse_status = 'unparsed'`.

Validates: file exists, JSON is a list, `DATABASE_URL` set.

## Stage 3: Parse (`parse_requirements.py`)

Reads `raw_prereq_text` / `raw_coreq_text`, writes structured rows, updates `parse_status`.

**Text handling:** normalize whitespace and labels; expand shorthand codes (`CMPUT 201 or 275`); split on `;`; infer `ALL_OF`, `ANY_OF`, `PREREQ`, `COREQ`, or `UNKNOWN`; extract level requirements as `requirement_text`; `normalize_parsed_groups` for nested logic.

**`parse_status`:**

| Value | Meaning |
|-------|---------|
| `parsed` | Structured, no unknown groups |
| `partial` | Some structure + unknown fragments |
| `unparsed` | No usable structure |

**Tables written:**

| Table | Contents |
|-------|----------|
| `requirement_groups` | Logic nodes (`group_type`, `parent_group_id`, display metadata) |
| `requirement_items` | Course FK, `missing_course_code`, or `requirement_text` |
| `course_edges` | `source` (prereq) → `target` (dependent), `edge_type` |

Per course: clears old parse rows, re-inserts, commits at end. Self-referencing course → aborts entire job. Missing referenced course → stored on item, no resolved edge.

## Operations

| Aspect | State |
|--------|--------|
| Schedule | Manual |
| Monitoring | Console output only |
| CI | `pytest` + compile; no live scrape |
