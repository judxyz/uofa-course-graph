"""Load scraped course data from JSON and upsert it into PostgreSQL."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable
from dotenv import load_dotenv
import psycopg

load_dotenv()

INPUT_PATH = Path(__file__).resolve().parent / "data" / "data_courses.json"

UPSERT_SQL = """
INSERT INTO courses (
    code,
    subject,
    number,
    title,
    description,
    other_notes,
    raw_prereq_text,
    raw_coreq_text,
    catalog_url,
    parse_status
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'unparsed')
ON CONFLICT (code) DO UPDATE SET
    subject = EXCLUDED.subject,
    number = EXCLUDED.number,
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    other_notes = EXCLUDED.other_notes,
    raw_prereq_text = EXCLUDED.raw_prereq_text,
    raw_coreq_text = EXCLUDED.raw_coreq_text,
    catalog_url = EXCLUDED.catalog_url,
    updated_at = NOW();
"""


def load_scraped_courses(path: Path = INPUT_PATH) -> list[dict[str, Any]]:
    """Load scraped course records from disk."""
    if not path.exists():
        raise FileNotFoundError(
            f"Scraped file not found: {path}. Run scraper.py first."
        )

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Expected scraped JSON to be a list of course objects.")

    return data


def upsert_courses(
    conn: psycopg.Connection,
    courses: list[dict[str, Any]],
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> None:
    """Insert or update course records in the database."""
    with conn.cursor() as cur:
        total = len(courses)
        for index, course in enumerate(courses, start=1):
            cur.execute(
                UPSERT_SQL,
                (
                    course["code"],          
                    course["subject"],
                    course["number"],
                    course["title"],
                    course.get("description"),
                    None,                    # other_notes for now
                    course.get("raw_prereq_text"),
                    course.get("raw_coreq_text"),
                    course.get("catalog_url"),
                ),
            )
            if progress_callback:
                progress_callback(index, total, course["code"])
    conn.commit()


def main() -> None:
    """Load scraped data from disk and write it to the database."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise EnvironmentError("DATABASE_URL is not set.")

    courses = load_scraped_courses()

    with psycopg.connect(database_url) as conn:
        upsert_courses(conn, courses)

    print(f"Updated {len(courses)} courses into PostgreSQL.")


if __name__ == "__main__":
    main()
