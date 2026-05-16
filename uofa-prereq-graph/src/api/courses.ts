import type { CourseDetails, CourseSearchItem } from '../types/course'
import { fetchJson, getApiBaseUrl } from './client'

export async function fetchCourses(): Promise<CourseSearchItem[]> {
  const url = new URL('/courses', getApiBaseUrl())
  return fetchJson<CourseSearchItem[]>(url)
}

export async function fetchCourse(code: string): Promise<CourseDetails> {
  const url = new URL(`/courses/${encodeURIComponent(code)}`, getApiBaseUrl())
  const response = await fetchJson<{
    id: number
    code: string
    title: string
    description: string | null
    other_notes: string | null
    raw_prereq_text: string | null
    raw_coreq_text: string | null
    catalog_url: string | null
    parse_status: CourseDetails['parseStatus']
  }>(url)

  return {
    id: response.id,
    code: response.code,
    title: response.title,
    description: response.description,
    otherNotes: response.other_notes,
    rawPrereqText: response.raw_prereq_text,
    rawCoreqText: response.raw_coreq_text,
    catalogUrl: response.catalog_url,
    parseStatus: response.parse_status,
  }
}
