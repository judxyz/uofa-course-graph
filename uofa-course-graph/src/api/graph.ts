import type { FetchCourseGraphOptions, GraphResponse } from '../types/graph'
import { normalizeCourseCode } from '../lib/courseCode'
import { fetchJson, getApiBaseUrl } from './client'

export async function fetchCourseGraph(
  code: string,
  options: FetchCourseGraphOptions = {},
): Promise<GraphResponse> {
  const trimmedCode = normalizeCourseCode(code)

  if (!trimmedCode) {
    throw new Error('A course code is required to load the graph.')
  }

  const url = new URL(`/graph/${encodeURIComponent(trimmedCode)}`, getApiBaseUrl())

  if (typeof options.maxDepth === 'number') {
    url.searchParams.set('max_depth', String(Math.max(0, options.maxDepth)))
  }

  if (typeof options.includeCoreqs === 'boolean') {
    url.searchParams.set('include_coreqs', String(options.includeCoreqs))
  }

  if (options.viewMode) {
    url.searchParams.set('view', options.viewMode)
  }

  return fetchJson<GraphResponse>(url)
}
