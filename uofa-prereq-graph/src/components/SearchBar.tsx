import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { fetchCourses } from '../api/courses'
import { formatCourseCodeForDisplay } from '../lib/courseCode'
import type { CourseSearchItem } from '../types/course'

interface SearchBarProps {
  onSelectCourse: (courseCode: string) => void
  initialValue?: string
}

function renderMatchText(text: string, query: string) {
  const normalizedQuery = query.trim().toLowerCase()

  if (!normalizedQuery) {
    return text
  }

  const startIndex = text.toLowerCase().indexOf(normalizedQuery)

  if (startIndex < 0) {
    return text
  }

  const endIndex = startIndex + normalizedQuery.length

  return (
    <>
      {text.slice(0, startIndex)}
      <span className="search-match-highlight">{text.slice(startIndex, endIndex)}</span>
      {text.slice(endIndex)}
    </>
  )
}

export function SearchBar({ onSelectCourse, initialValue = '' }: SearchBarProps) {
  const [query, setQuery] = useState(formatCourseCodeForDisplay(initialValue))
  const [courses, setCourses] = useState<CourseSearchItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const searchRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let isCancelled = false

    async function loadCourses() {
      try {
        const result = await fetchCourses()

        if (!isCancelled) {
          setCourses(result)
        }
      } catch (unknownError) {
        if (!isCancelled) {
          const message =
            unknownError instanceof Error ? unknownError.message : 'Unable to load courses.'
          setError(message)
        }
      }
    }

    void loadCourses()

    return () => {
      isCancelled = true
    }
  }, [])

  useEffect(() => {
    setQuery(formatCourseCodeForDisplay(initialValue))
  }, [initialValue])

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!searchRef.current?.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
    }
  }, [])

  const filteredCourses = useMemo(() => {
    const normalized = query.trim().toLowerCase()

    if (normalized.length < 2) {
      return []
    }

    return courses
      .map((course) => {
        const code = course.code.toLowerCase()

        if (code.startsWith(normalized)) {
          return { course, rank: 0 }
        }

        if (code.includes(normalized)) {
          return { course, rank: 1 }
        }

        return null
      })
      .filter((entry): entry is { course: CourseSearchItem; rank: number } => entry !== null)
      .sort((left, right) => {
        if (left.rank !== right.rank) {
          return left.rank - right.rank
        }

        return left.course.code.localeCompare(right.course.code)
      })
      .map((entry) => entry.course)
      .slice(0, 3)
  }, [courses, query])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedQuery = query.trim()

    if (!trimmedQuery) {
      return
    }

    setIsOpen(false)
    onSelectCourse(formatCourseCodeForDisplay(trimmedQuery))
  }

  function handleSelectCourse(course: CourseSearchItem) {
    setQuery(course.code)
    setIsOpen(false)
    onSelectCourse(formatCourseCodeForDisplay(course.code))
  }

  return (
    <section ref={searchRef} className="search-block" aria-label="Course search">
      <form className="search-form" role="search" onSubmit={handleSubmit}>
        <div className="search-input-shell">
          <label htmlFor="course-search-input" className="search-prefix">
            Search Course:
          </label>
          <input
            id="course-search-input"
            type="search"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value)
              setIsOpen(true)
            }}
            onFocus={() => setIsOpen(true)}
            placeholder="eg. CMPUT 267"
            aria-label="Search for a course code"
            aria-expanded={isOpen}
            aria-controls="course-search-results"
            className="search-form-input"
            autoComplete="off"
          />
        </div>
      </form>
      {error ? <p className="search-error">{error}</p> : null}
      {isOpen && filteredCourses.length > 0 ? (
        <div id="course-search-results" className="search-results" role="listbox">
          {filteredCourses.map((course) => (
            <button
              key={course.code}
              type="button"
              onClick={() => handleSelectCourse(course)}
              className="search-result-button"
            >
              <span className="search-result-code">{renderMatchText(course.code, query)}</span>
              <span className="search-result-title">{renderMatchText(course.title, query)}</span>
            </button>
          ))}
        </div>
      ) : isOpen && query.trim().length >= 2 ? (
        <div className="search-results">
          <p className="search-results-empty">No results found.</p>
        </div>
      ) : null}
    </section>
  )
}
