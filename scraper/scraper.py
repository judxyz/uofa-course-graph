"""Scrape course data from the UAlberta catalogue."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

import requests
from bs4 import BeautifulSoup, Tag, NavigableString
from scrape_catalog_subjects import fetch_subject_slugs


FALLBACK_CATALOG_SUBJECTS = ["ai", "astro", "bioin", "biol", "bioph", "bot", "chem", "data", "eas", "en_ph", "ent", "genet", "geoph", "imin", "int_d", "ipg", "ma_ph", "ma_sc", "math", "micrb", "mint", "mm", "paleo", "phys", "plan", "psych", "sci", "stat", "wkexp", "zool"]

CATALOG_URL = "https://apps.ualberta.ca/catalogue/course/"
BASE_URL = "https://apps.ualberta.ca"
_DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_PATH = _DATA_DIR / "data_courses.json"

@dataclass
class RawCourse:
    code: str
    subject: str
    number: str
    title: str
    units: int
    description: str
    raw_prereq_text: Optional[str]
    raw_coreq_text: Optional[str]
    catalog_url: Optional[str]
    


def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace into single spaces."""
    # replace any whitespace \s with ' '
    return re.sub(r"\s+", " ", text).strip()

def extract_units(text: str) -> Optional[int]:
    """Extract the unit count from a course detail string."""
    match = re.search(r"\b(\d+)\s+units?\b", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None

def extract_requirement_section(text: str, label: str) -> Optional[str]:
    """
    Extract a prerequisite/corequisite sentence starting at its label.

    Catalogue entries often use semicolons inside a single requirement
    sentence, so we stop at the sentence-ending period rather than the first
    semicolon.
    """
    pattern = re.compile(
        rf"{label}[s]?:\s*(.*?)(?:\.(?:\s|$)|$)",
        flags=re.IGNORECASE,
    )
    match = pattern.search(text)

    if not match:
        return None

    section = normalize_whitespace(match.group(1)).rstrip(" .;")

    section = re.sub(
        r"\s*;\s*and permission of the Department\s*$",
        "",
        section,
        flags=re.IGNORECASE,
    )

    return section.rstrip(" .;")

def extract_prereq_text(text: str) -> Optional[str]:
    """Extract prerequisite text when it contains course-like codes."""
    prereq_text = extract_requirement_section(text, "Prerequisite")

    if not prereq_text:
        return None

    # Ignore things like:
    # "Second-year standing"
    # "Math 30, 30-1, or 30-2"
    # unless an actual university course code appears
    if not re.search(r"\b[A-Z]{2,10}\s*\d{3}[A-Z]?\b", prereq_text):
        return None

    return prereq_text

def extract_coreq_text(text: str) -> Optional[str]:
    """Extract corequisite text when it contains course-like codes."""
    coreq_text = extract_requirement_section(text, "Corequisite")

    if not coreq_text:
        return None

    # Ignore things like:
    # "Second-year standing"
    # "Math 30, 30-1, or 30-2"
    # unless an actual university course code appears
    if not re.search(r"\b[A-Z]{2,10}\s*\d{3}[A-Z]?\b", coreq_text):
        return None

    return coreq_text


def fetch_html(subject_slug: Optional[str] = None) -> str:
    """Download the HTML for the catalogue page."""
    url = f"{CATALOG_URL}{subject_slug}" if subject_slug else CATALOG_URL
    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
    )
    response.raise_for_status()
    return response.text



def extract_catalog_url(heading: Tag) -> Optional[str]:
    """Extract an absolute catalogue URL from a course heading."""
    link = heading.find("a")
    if not link or not link.get("href"):
        return None

    href = link["href"]
    if href.startswith("http"):
        return href
    return f"{BASE_URL}{href}"

def parse_heading(text: str) -> Optional[tuple[str, str, str, str]]:
    """Parse a course heading into code, number, and title."""
    text = normalize_whitespace(text)
    text = re.sub(r"^Effective:\s*\d{4}-\d{2}-\d{2}\s+", "", text)

    match = re.match(r"^([A-Z][A-Z ]{1,14})\s+([0-9A-Z]+(?:[A-Z])?)\s+-\s+(.+)$", text)
    if not match:
        return None

    subject, number, title = match.groups()
    subject = normalize_whitespace(subject)
    code = f"{subject} {number}"
    return code, subject, number, title


def parse_courses(html: str) -> list[RawCourse]:
    """Parse course entries from catalogue HTML."""
    soup = BeautifulSoup(html, "html.parser")
    course_blocks = soup.select("div.course")

    courses: list[RawCourse] = []
    seen_codes: set[str] = set()

    for block in course_blocks:
        heading = block.find("h2")
        if not heading:
            continue

        heading_text = normalize_whitespace(heading.get_text(" ", strip=True))
        parsed = parse_heading(heading_text)
        if not parsed:
            continue

        code, subject, number, title = parsed

        # skip duplicate effective versions
        if code in seen_codes:
            continue

        link = heading.find("a", href=True)
        catalog_url = f"{BASE_URL}{link['href']}" if link else None

        body_divs = block.find_all("div", recursive=False)
        if len(body_divs) < 2:
            continue

        content_div = body_divs[1]

        units_text = normalize_whitespace(content_div.get_text(" ", strip=True))
        units = extract_units(units_text)
        if units is None:
            continue

        if units == 0:
            continue



        if re.search(r"[A-Z]$", code): # skip CMPUT 499B
            continue

        description_tag = content_div.find("p")
        description = normalize_whitespace(description_tag.get_text(" ", strip=True)) if description_tag else ""

        if description == "":
            continue
        
        full_text = normalize_whitespace(content_div.get_text(" ", strip=True))

        course = RawCourse(
            code=code,
            subject=subject,
            number=number,
            title=title,
            units=units,
            description=description,
            raw_prereq_text=extract_prereq_text(full_text),
            raw_coreq_text=extract_coreq_text(full_text),
            catalog_url=catalog_url,
        )

        courses.append(course)
        seen_codes.add(code)

    return courses


def save_raw_json(courses: List[RawCourse], output_path: Path = OUTPUT_PATH) -> None:
    """Write scraped course data to JSON on disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([asdict(course) for course in courses], indent=2),
        encoding="utf-8",
    )


def scrape_all_courses() -> list[RawCourse]:
    """Scrape all configured catalogue subjects and return deduplicated courses."""
    courses: list[RawCourse] = []
    seen_codes: set[str] = set()

    try:
        catalog_subjects = fetch_subject_slugs()
        print(f"Found {len(catalog_subjects)} catalogue subjects")
    except requests.RequestException as exc:
        catalog_subjects = FALLBACK_CATALOG_SUBJECTS
        print(f"Using fallback catalogue subjects: failed to fetch subject list ({exc})")

    for subject_slug in catalog_subjects:
        try:
            html = fetch_html(subject_slug)
        except requests.RequestException as exc:
            print(f"Skipping {subject_slug}: failed to fetch ({exc})")
            continue

        subject_courses = parse_courses(html)
        new_courses = 0
        for course in subject_courses:
            if course.code in seen_codes:
                continue
            courses.append(course)
            seen_codes.add(course.code)
            new_courses += 1

        print(f"{subject_slug}: +{new_courses} courses")

    return courses


def main() -> None:
    """Scrape catalogue data and save it as JSON."""
    courses = scrape_all_courses()

    save_raw_json(courses)

    print(f"Scraped {len(courses)} non-zero-unit courses")
    for course in courses[:5]:
        print(f"- {course.code}: {course.title} ({course.units} units)")


if __name__ == "__main__":
    main()
