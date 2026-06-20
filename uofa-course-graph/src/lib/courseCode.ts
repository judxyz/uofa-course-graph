/** Default graph when opening the app at `/` (kept in sync with API `GET /` → `default_course`). */
export const DEFAULT_GRAPH_COURSE_DISPLAY = 'CMPUT 267'

export function normalizeCourseCode(value: string) {
  return value
    .trim()
    .toUpperCase()
    .replace(/[-\s]+/g, ' ')
}

export function formatCourseCodeForRoute(value: string) {
  return normalizeCourseCode(value).replace(/\s+/g, '-')
}

export function formatCourseCodeForDisplay(value: string) {
  return normalizeCourseCode(value)
}
