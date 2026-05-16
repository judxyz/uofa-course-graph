# Course catalogue scraper

Offline pipeline to scrape the UAlberta course catalogue, save raw JSON, and upsert rows into PostgreSQL.

## Layout

- `scraper.py` — fetch and parse course pages → `data/data_courses.json`
- `scrape_catalog_subjects.py` — discover subject slugs from the catalogue index
- `add_to_db.py` — upsert JSON into the `courses` table
- `run_scrape_add.py` — scrape and load in one command
- `parse_requirements.py` — parse prerequisite text into requirement groups (DB-backed jobs)
- `tests/` — parser unit tests

## Environment

- `DATABASE_URL` — required for `add_to_db.py`, `run_scrape_add.py`, and `parse_requirements.py`

## Setup

From the repository root:

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Scrape only (writes data/data_courses.json)
python scraper.py

# Load existing JSON
python add_to_db.py

# Scrape + load
python run_scrape_add.py
```

## Tests

From the repository root:

```bash
pip install -r requirements-dev.txt
cd scraper
pytest
```
