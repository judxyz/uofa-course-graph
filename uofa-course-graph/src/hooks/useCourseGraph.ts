import { useEffect, useState } from 'react'
import { fetchCourseGraph } from '../api/graph'
import type { FetchCourseGraphOptions, GraphResponse, GraphViewMode } from '../types/graph'

export interface UseCourseGraphState {
  selectedCourseCode: string
  params: Required<FetchCourseGraphOptions>
  maxDepth: number
  includeCoreqs: boolean
  viewMode: GraphViewMode
  graph: GraphResponse | null
  isLoading: boolean
  error: string | null
  setSelectedCourseCode: (code: string) => void
  setMaxDepth: (depth: number) => void
  setIncludeCoreqs: (include: boolean) => void
  setViewMode: (mode: GraphViewMode) => void
}

export function useCourseGraph(initialCourseCode = '', initialMaxDepth = 1): UseCourseGraphState {
  const [selectedCourseCode, setSelectedCourseCode] = useState(initialCourseCode)
  const [params, setParams] = useState<Required<FetchCourseGraphOptions>>({
    maxDepth: initialMaxDepth,
    includeCoreqs: false,
    viewMode: 'prereq',
  })
  const [graph, setGraph] = useState<GraphResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setSelectedCourseCode(initialCourseCode)
  }, [initialCourseCode])

  useEffect(() => {
    const normalizedCode = selectedCourseCode.trim()

    if (!normalizedCode) {
      setGraph(null)
      setError(null)
      setIsLoading(false)
      return
    }

    let isCancelled = false

    async function loadGraph() {
      setIsLoading(true)
      setError(null)

      try {
        const response = await fetchCourseGraph(normalizedCode, params)

        if (!isCancelled) {
          setGraph(response)
        }
      } catch (unknownError) {
        if (!isCancelled) {
          const message =
            unknownError instanceof Error ? unknownError.message : 'An unknown error occurred.'
          setError(message)
          setGraph(null)
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadGraph()

    return () => {
      isCancelled = true
    }
  }, [selectedCourseCode, params])

  function setMaxDepth(depth: number) {
    setParams((current) => ({
      ...current,
      maxDepth: depth,
    }))
  }

  function setIncludeCoreqs(include: boolean) {
    setParams((current) => ({
      ...current,
      includeCoreqs: include,
    }))
  }

  function setViewMode(mode: GraphViewMode) {
    setParams((current) => ({
      ...current,
      viewMode: mode,
      // Dependency mode is intentionally one-level, prerequisite-only.
      maxDepth: mode === 'dependency' ? 1 : current.maxDepth,
      includeCoreqs: mode === 'dependency' ? false : current.includeCoreqs,
    }))
  }

  return {
    selectedCourseCode,
    params,
    maxDepth: params.maxDepth,
    includeCoreqs: params.includeCoreqs,
    viewMode: params.viewMode,
    graph,
    isLoading,
    error,
    setSelectedCourseCode,
    setMaxDepth,
    setIncludeCoreqs,
    setViewMode,
  }
}
