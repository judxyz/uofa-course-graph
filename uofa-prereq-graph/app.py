"""FastAPI application for serving course and prerequisite graph data."""

from __future__ import annotations

import os
from typing import Literal
from dotenv import load_dotenv

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from graph_builder import GraphBuilder, normalize_course_code

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL is not set.")


def _cors_allow_origins() -> list[str]:
    origins = [
        "https://uofa-prereq-graph.vercel.app",
        "http://localhost:5173",
    ]
    extra = os.environ.get("CORS_EXTRA_ORIGINS", "")
    for raw in extra.split(","):
        o = raw.strip()
        if o:
            origins.append(o)
    return origins


app = FastAPI(title="CMPUT Prerequisite Graph API")

DEFAULT_GRAPH_COURSE = "CMPUT 267"


@app.get("/")
def root():
    """Identify the API and the course code shown when the web app opens at /."""
    return {
        "service": "cmput-prereq-api",
        "default_course": DEFAULT_GRAPH_COURSE,
    }


app.add_middleware(
    CORSMiddleware,
    # Deployed + local Vite; add LAN dev via CORS_EXTRA_ORIGINS (comma-separated).
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn():
    """Create a database connection using the configured database URL."""
    return psycopg.connect(DATABASE_URL, prepare_threshold=None)


# --------------------------------------------------
# Health
# --------------------------------------------------

@app.get("/health")
def health():
    """Return a simple health status payload for the API."""
    return {
        "status": "ok",
        "service": "cmput-prereq-api",
    }


# --------------------------------------------------
# Courses
# --------------------------------------------------

@app.get("/courses")
def get_courses():
    """List courses with their codes and titles."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT code, title
                FROM courses
                ORDER BY subject, number
                """
            )
            rows = cur.fetchall()

    return [{"code": code, "title": title} for code, title in rows]


@app.get("/courses/{code}")
def get_course(code: str):
    """Fetch a single course by code."""
    normalized_code = normalize_course_code(code)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    code,
                    title,
                    description,
                    other_notes,
                    raw_prereq_text,
                    raw_coreq_text,
                    catalog_url,
                    parse_status
                FROM courses
                WHERE UPPER(code) = %s
                """,
                (normalized_code,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Course not found")

    (
        course_id,
        code_value,
        title,
        description,
        other_notes,
        raw_prereq_text,
        raw_coreq_text,
        catalog_url,
        parse_status,
    ) = row

    return {
        "id": course_id,
        "code": code_value,
        "title": title,
        "description": description,
        "other_notes": other_notes,
        "raw_prereq_text": raw_prereq_text,
        "raw_coreq_text": raw_coreq_text,
        "catalog_url": catalog_url,
        "parse_status": parse_status,
    }


# --------------------------------------------------
# Graph
# --------------------------------------------------

@app.get("/graph/{code}")
def get_graph(
    code: str,
    max_depth: int = Query(1, ge=0, le=8),
    include_coreqs: bool = Query(True),
    view: Literal["prereq", "dependency"] = Query("prereq"),
):
    """
    Build recursive frontend graph data for a course.

    max_depth is the maximum prerequisite course depth included:
    - 0 = root course only
    - 1 = include direct prerequisite/corequisite courses
    - 2 = include prerequisites of those courses
    - etc. Requirement group nodes do not count against this limit.
    """
    with get_conn() as conn:
        builder = GraphBuilder(
            conn=conn,
            max_depth=max_depth,
            include_coreqs=include_coreqs,
        )

        try:
            if view == "dependency":
                return builder.build_dependency_from_code(code)
            return builder.build_from_code(code)
        except ValueError:
            raise HTTPException(status_code=404, detail="Course not found") from None

from mangum import Mangum

handler = Mangum(app)