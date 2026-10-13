"""Scrape course data and load the results into the database."""

from __future__ import annotations

import os

import psycopg

from dotenv import load_dotenv
from scraper import scrape_all_courses, save_raw_json
from c_add_to_db import upsert_courses
load_dotenv()

def main() -> None:
    """Run the scrape-and-upsert workflow."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise EnvironmentError("DATABASE_URL is not set.")

    print("Starting catalogue scrape...", flush=True)
    courses = scrape_all_courses()

    print(f"Scrape complete: {len(courses)} courses found.", flush=True)
    print("Saving scraped JSON...", flush=True)
    save_raw_json(courses)
    print("Scraped JSON saved.", flush=True)

    print("Upserting courses into PostgreSQL...", flush=True)
    with psycopg.connect(database_url) as conn:
        upsert_courses(
            conn,
            [course.__dict__ for course in courses],
            progress_callback=lambda index, total, code: print(
                f"Database upsert: {index}/{total} ({code})",
                flush=True,
            ),
        )

    print(f"Complete: {len(courses)} courses saved to database.", flush=True)


if __name__ == "__main__":
    main()
