"""Fetch UAlberta catalogue subject endpoints.

This utility scrapes the catalogue subject index and prints a copy-pasteable
Python list of subject slugs such as "cmput" and "biol".
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


CATALOG_SUBJECTS_URL = "https://apps.ualberta.ca/catalogue/course"
COURSE_PATH_RE = re.compile(r"^/catalogue/course/([^/?#]+?)/?$")


def fetch_subject_slugs(url: str = CATALOG_SUBJECTS_URL) -> list[str]:
    """Return all catalogue subject endpoint slugs from the subjects page."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    slugs: set[str] = set()

    for anchor in soup.select("a[href]"):
        href = anchor.get("href")
        if not href:
            continue

        absolute_url = urljoin(url, href)
        path = urlparse(absolute_url).path
        match = COURSE_PATH_RE.match(path)

        if match:
            slugs.add(match.group(1))

    return sorted(slugs)


def main() -> None:
    """Print subject slugs in human-readable and machine-readable forms."""
    slugs = fetch_subject_slugs()

    print(f"Found {len(slugs)} subject endpoints.")
    print("\nPython list:")
    print(f"CATALOG_SUBJECTS = {json.dumps(slugs, indent=2)}")

    print("\nOne per line:")
    for slug in slugs:
        print(slug)


if __name__ == "__main__":
    main()
