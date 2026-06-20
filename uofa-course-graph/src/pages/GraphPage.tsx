import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { GraphCanvas } from '../components/GraphCanvas'
import { SearchBar } from '../components/SearchBar'
import { useCourseGraph } from '../hooks/useCourseGraph'
import {
  DEFAULT_GRAPH_COURSE_DISPLAY,
  formatCourseCodeForDisplay,
  formatCourseCodeForRoute,
} from '../lib/courseCode'

const COURSE_DEPTH_OPTIONS = [1, 2, 3, 4]

function courseCodeFromRouteParam(code: string | undefined) {
  const raw = (code ?? '').trim()
  return raw ? formatCourseCodeForDisplay(raw) : DEFAULT_GRAPH_COURSE_DISPLAY
}

export function GraphPage() {
  const { code } = useParams()
  const navigate = useNavigate()
  const [isDepthMenuOpen, setIsDepthMenuOpen] = useState(false)
  const depthFilterRef = useRef<HTMLDivElement | null>(null)
  const {
    selectedCourseCode,
    graph,
    error,
    maxDepth,
    includeCoreqs,
    viewMode,
    setSelectedCourseCode,
    setMaxDepth,
    setIncludeCoreqs,
    setViewMode,
  } = useCourseGraph(courseCodeFromRouteParam(code))

  useEffect(() => {
    setSelectedCourseCode(courseCodeFromRouteParam(code))
  }, [code, setSelectedCourseCode])

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!depthFilterRef.current?.contains(event.target as Node)) {
        setIsDepthMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
    }
  }, [])

  return (
    <main className="app-shell">
      <header className="app-topbar">
        <div className="app-topbar-stack">
          <section className="app-topbar-shell">
            <div className="app-topbar-left">
              <h1 className="app-title">UofA Course Graph </h1>
              <h3 className="app-subtitle">
                {viewMode === 'dependency' ? 'Dependency View' : 'Prerequisite View'}
              </h3>
              <SearchBar
                initialValue={selectedCourseCode}
                onSelectCourse={(courseCode) => navigate(`/graph/${formatCourseCodeForRoute(courseCode)}`)}
              />
              {viewMode === 'prereq' ? (
                <>
                  <div ref={depthFilterRef} className="depth-filter">
                    <span id="depth-filter-label" className="depth-filter-label">
                      Prerequisite depth:
                    </span>
                    <button
                      type="button"
                      className="depth-filter-button"
                      aria-labelledby="depth-filter-label"
                      aria-haspopup="listbox"
                      aria-expanded={isDepthMenuOpen}
                      onClick={() => setIsDepthMenuOpen((open) => !open)}
                    >
                      {maxDepth === 1 ? '1 level' : `${maxDepth} levels`}
                    </button>
                    {isDepthMenuOpen ? (
                      <div className="depth-filter-menu" role="listbox" aria-labelledby="depth-filter-label">
                        {COURSE_DEPTH_OPTIONS.map((depth) => (
                          <button
                            key={depth}
                            type="button"
                            className={`depth-filter-option${depth === maxDepth ? ' depth-filter-option--active' : ''}`}
                            role="option"
                            aria-selected={depth === maxDepth}
                            onClick={() => {
                              setMaxDepth(depth)
                              setIsDepthMenuOpen(false)
                            }}
                          >
                            {depth === 1 ? '1 level' : `${depth} levels`}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <label className="coreq-toggle">
                    <input
                      type="checkbox"
                      checked={includeCoreqs}
                      onChange={(event) => setIncludeCoreqs(event.target.checked)}
                    />
                    <span>Display corequisites</span>
                  </label>
                </>
              ) : null}
              <button
                type="button"
                className="view-mode-toggle"
                onClick={() => setViewMode(viewMode === 'prereq' ? 'dependency' : 'prereq')}
              >
                {viewMode === 'prereq' ? 'Switch to Dependency View' : 'Switch to Prerequisite View'}
              </button>
            </div>
          </section>
        </div>
      </header>

      {error ? <div className="app-status app-status-error" role="alert">{error}</div> : null}

      <section className="graph-section">
        <GraphCanvas graph={graph} />
      </section>
    </main>
  )
}
