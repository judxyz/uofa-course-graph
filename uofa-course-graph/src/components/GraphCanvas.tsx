import { useEffect, useRef, useState } from 'react'
import { DataSet } from 'vis-data'
import { Network } from 'vis-network'
import type { Edge, Node, Options } from 'vis-network'
import { fetchCourse } from '../api/courses'
import type { GraphNode, GraphResponse, GroupType } from '../types/graph'

interface GraphCanvasProps {
  graph: GraphResponse | null
}

interface SelectedCourseState {
  code: string
  title: string
  description: string
  catalogUrl: string | null
  error: string | null
}

const OR_COLOR = '#2e3fa2'
const OR_COLOR_BG = '#e6e8f2'
const AND_COLOR = '#752020'
const AND_COLOR_BG = '#752020'
const PREREQ_COLOR = '#752020'
const PREREQ_COLOR_BG = '#752020'

const MOBILE_GRAPH_QUERY = '(max-width: 720px), (pointer: coarse)'
const UI_FONT_FAMILY = 'Inter, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
const ZOOM_BUTTON_ANIMATION = {
  duration: 400,
  easingFunction: 'easeInOutQuad' as const,
}

const baseGraphOptions: Options = {
  autoResize: true,
  layout: {
    hierarchical: {
      enabled: true,
      direction: 'UD',
      sortMethod: 'directed',
      shakeTowards: 'roots',
      levelSeparation: 133,
      nodeSpacing: 150,
      treeSpacing: 500,
      
    },
  },
  physics: false,
  interaction: {
    dragNodes: false,
    dragView: true,
    hover: true,
    zoomView: true,
    navigationButtons: false,
  },
  nodes: {
    font: {
      face: UI_FONT_FAMILY,
      color: '#173122',
      size: 15,
    },
    borderWidth: 1.25,
    shadow: {
      enabled: false,
    },
    scaling: {
      label: {
        drawThreshold: 1,
      },
    },
  },
  edges: {
    arrows: {
      to: {
        enabled: true,
        scaleFactor: 0.95,
      },
    },
    color: {
      color: PREREQ_COLOR,
      highlight: PREREQ_COLOR,
      hover: PREREQ_COLOR,
    },
    smooth: false,
    width: 1.35,
  },
}

function getGraphOptions(isMobile: boolean): Options {
  const interaction = baseGraphOptions.interaction ?? {}

  return {
    ...baseGraphOptions,
    interaction: {
      ...interaction,
      // Hover hit-testing is expensive on touch devices and not useful there.
      hover: isMobile ? false : interaction.hover,
      tooltipDelay: isMobile ? 240 : 120,
      zoomSpeed: isMobile ? 0.7 : 0.3,
    },
  }
}

function buildFallbackCatalogUrl(code: string) {
  const [subject = '', number = ''] = code.split(/\s+/)

  if (!subject || !number) {
    return null
  }

  return `https://apps.ualberta.ca/catalogue/course/${subject.toLowerCase()}/${number.toLowerCase()}`
}

function getCoursePanelHeading(code: string) {
  const compact = code.replace(/\s+/g, '')
  return compact.length <= 8 ? compact : code
}

function getGroupStyle(groupType: GroupType, visualStyle: string | null) {
  if (groupType === 'ALL_OF') {
    return {
      shape: 'box',
      label: 'AND',
      background: AND_COLOR,
      border: AND_COLOR_BG,
      fontColor: '#ffffff',
      size: undefined,
      widthConstraint: {
        minimum: 96,
        maximum: 96,
      },
      heightConstraint: undefined,

    }
  }

  if (groupType === 'ANY_OF') {
    return {
      shape: 'ellipse',
      label: 'OR',
      background: OR_COLOR,
      border: OR_COLOR_BG,
      fontColor: '#ffffff',
      size: undefined,
      widthConstraint: 84,
      heightConstraint: undefined,
    }
  }

  if (groupType === 'COREQ') {
    if (visualStyle === 'or') {
      return {
        shape: 'ellipse',
        label: 'OR',
        background: OR_COLOR,
        border: OR_COLOR_BG,
        fontColor: '#ffffff',
        size: undefined,
        widthConstraint: 84,
        heightConstraint: undefined,
      }
    }

    if (visualStyle === 'and') {
      return {
        shape: 'box',
        label: 'AND',
        background: AND_COLOR_BG,
        border: AND_COLOR,
        fontColor: AND_COLOR,
        size: undefined,
        widthConstraint: {
          minimum: 96,
          maximum: 96,
        },
        heightConstraint: undefined,
      }
    }

    return {
      shape: 'box',
      label: 'COREQ',
      background: PREREQ_COLOR,
      border: PREREQ_COLOR_BG,
      fontColor: '#ffffff',
      size: undefined,
      widthConstraint: {
        minimum: 96,
        maximum: 96,
      },
      heightConstraint: undefined,

    }
  }
  

  return {
    shape: 'box',
    label: groupType,
    background: PREREQ_COLOR_BG,
    border: PREREQ_COLOR,
    fontColor: '#ffffff',
    size: undefined,
    widthConstraint: 84,
    heightConstraint: undefined,
  }
}

function getEdgeColor(groupType: GroupType | null, isCoreq: boolean) {
  if (isCoreq || groupType === 'COREQ') {
    return PREREQ_COLOR
  }

  if (groupType === 'ANY_OF') {
    return OR_COLOR
  }

  if (groupType === 'ALL_OF') {
    return AND_COLOR
  }

  return PREREQ_COLOR
}

function isOrGroupNode(node: GraphNode | undefined) {
  if (!node || node.type !== 'group') {
    return false
  }

  if (node.groupType === 'ANY_OF') {
    return true
  }

  return node.groupType === 'COREQ' && (node.visualStyle ?? '').trim().toLowerCase() === 'or'
}

function isDependencyView(graph: GraphResponse) {
  return graph.meta.viewMode === 'dependency'
}

function getPrereqCourseFill(depth: number) {
  const depthColorMap: Record<number, string> = {
    1: '#235432',
    2: '#275D38',
    3: '#688E74',
    4: '#a9beaf',
  }
  // Course nodes are separated by group nodes, so course depths are 0,2,4,6...
  // Convert node depth to prerequisite course level: 2->1, 4->2, 6->3, 8+->4.
  const courseLevel = Math.ceil(depth / 2)
  const normalizedLevel = Math.max(1, Math.min(4, courseLevel))
  return depthColorMap[normalizedLevel]
}

function toVisNodes(graph: GraphResponse): Node[] {
  const isPrereqView = !isDependencyView(graph)

  return graph.nodes.map((node) => {
    if (node.type === 'course') {
      const isRoot = node.courseId === graph.rootCourse.id
      const isUnavailable = node.isAvailable === false
      const prerequisiteFill = getPrereqCourseFill(node.depth)
      const isFirstOrSecondCourseLevel = node.depth === 2 || node.depth === 4 || node.depth === 3

      return {
        id: node.id,
        label: node.code,
        level: node.depth,
        shape: 'box',
        borderWidth: 1.25,
        margin: {
          top: 12,
          right: 18,
          bottom: 12,
          left: 18,
        },
        color: isRoot
          ? {
              background: '#1B4127',
              border: '#1B4127',
              highlight: {
                background: '#1B4127',
                border: '#173122',
              },
              hover: {
                background: '#1B4127',
                border: '#173122',
              },
            }
          : isUnavailable
            ? {
                background: '#ffffff',
                border: '#c8d6cc',
                borderWidth: 1.25,
                highlight: {
                  background: '#f5f8f5',
                  border: '#1B4127',
                },
                hover: {
                  background: '#f5f8f5',
                  border: '#1B4127',
                },
              }
            : {
                background: isPrereqView ? prerequisiteFill : '#752020',
                border: isPrereqView ? '#1B4127' : '#752020',
                highlight: {
                  background: isPrereqView ? prerequisiteFill : '#8b3a3a',
                  border: isPrereqView ? '#1B4127' : '#a96a6a',
                },
                hover: {
                  background: isPrereqView ? prerequisiteFill : '#843232',
                  border: isPrereqView ? '#1B4127' : '#9b5656',
                },
              },
        font: {
          color: isUnavailable ? '#2f2740' : isRoot || isFirstOrSecondCourseLevel || !isPrereqView ? '#ffffff' : '#000000',
          size: isRoot ? 17 : 15,
          face: UI_FONT_FAMILY,
          bold: isRoot ? '700' : isUnavailable ? '400' : '500',
        },
        widthConstraint: {
          minimum: 96,
          maximum: 140,
        },
      }
    }

    if (node.type === 'requirement') {
      const prerequisiteFill = getPrereqCourseFill(node.depth)
      const isFirstOrSecondCourseLevel = node.depth === 2 || node.depth === 4 || node.depth === 3

      return {
        id: node.id,
        label: node.label,
        level: node.depth,
        shape: 'box',
        borderWidth: 1.25,
        margin: {
          top: 12,
          right: 18,
          bottom: 12,
          left: 18,
        },
        color: {
          background: isPrereqView ? prerequisiteFill : '#752020',
          border: isPrereqView ? '#1B4127' : '#752020',
          highlight: {
            background: isPrereqView ? prerequisiteFill : '#8b3a3a',
            border: isPrereqView ? '#1B4127' : '#a96a6a',
          },
          hover: {
            background: isPrereqView ? prerequisiteFill : '#843232',
            border: isPrereqView ? '#1B4127' : '#9b5656',
          },
        },
        font: {
          color: isFirstOrSecondCourseLevel || !isPrereqView ? '#ffffff' : '#000000',
          size: 15,
          face: UI_FONT_FAMILY,
          bold: '500',
        },
        widthConstraint: {
          minimum: 96,
          maximum: 140,
        },
      }
    }

    const groupStyle = getGroupStyle(node.groupType, node.visualStyle)

    return {
      id: node.id,
      label: groupStyle.label,
      level: node.depth,
      shape: groupStyle.shape,
      color: {
        background: groupStyle.background,
        border: groupStyle.border,
        highlight: {
          background: groupStyle.background,
          border: groupStyle.border,
        },
        hover: {
          background: groupStyle.background,
          border: groupStyle.border,
        },
      },
      font: {
        color: groupStyle.fontColor,
        size: 12,
        face: UI_FONT_FAMILY,
        bold: node.groupType === 'UNKNOWN' ? '500' : '700',
      },
      size: groupStyle.size,
      widthConstraint: groupStyle.widthConstraint,
      heightConstraint: groupStyle.heightConstraint,
    }
  })
}

function toVisEdges(graph: GraphResponse): Edge[] {
  const nodeLookup = new Map(graph.nodes.map((node) => [node.id, node]))
  const reverseDirection = isDependencyView(graph)

  return graph.edges.map((edge) => {
    const sourceNode = nodeLookup.get(edge.source)
    const targetNode = nodeLookup.get(edge.target)
    const sourceGroupType = sourceNode?.type === 'group' ? sourceNode.groupType : null
    const targetGroupType = targetNode?.type === 'group' ? targetNode.groupType : null
    const groupType = sourceGroupType ?? targetGroupType
    const isTowardOrNode = isOrGroupNode(targetNode)
    const isAwayFromOrNode = isOrGroupNode(sourceNode)
    const relationBaseColor = PREREQ_COLOR
    const edgeColor = isTowardOrNode
      ? relationBaseColor
      : isAwayFromOrNode
        ? OR_COLOR
        : getEdgeColor(groupType, edge.relationType === 'COREQ')
    const from = reverseDirection ? edge.target : edge.source
    const to = reverseDirection ? edge.source : edge.target

    return {
      id: edge.id,
      from,
      to,
      dashes: edge.relationType === 'COREQ',
      color: {
        color: edgeColor,
        highlight: edgeColor,
        hover: edgeColor,
      },
    }
  })
}

function graphResetKey(graph: GraphResponse | null): string {
  if (!graph) {
    return 'empty'
  }
  return `${graph.rootCourse.code}:${graph.edges.length}:${graph.nodes.length}`
}

export function GraphCanvas({ graph }: GraphCanvasProps) {
  return <GraphCanvasView key={graphResetKey(graph)} graph={graph} />
}

function GraphCanvasView({ graph }: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const helpRef = useRef<HTMLDivElement | null>(null)
  const networkRef = useRef<Network | null>(null)
  const requestIdRef = useRef(0)
  const panelOpenFrameRef = useRef<number | null>(null)
  const [selectedCourse, setSelectedCourse] = useState<SelectedCourseState | null>(null)
  const [panelPhase, setPanelPhase] = useState<'hidden' | 'open'>('hidden')
  const [showHelp, setShowHelp] = useState(false)
  const [showLegend, setShowLegend] = useState(false)

  function clearPanelTimers() {
    if (panelOpenFrameRef.current !== null) {
      window.cancelAnimationFrame(panelOpenFrameRef.current)
      panelOpenFrameRef.current = null
    }
  }

  function hideCoursePanelImmediately() {
    clearPanelTimers()
    setPanelPhase('hidden')
    setSelectedCourse(null)
  }

  function showCoursePanel(course: SelectedCourseState) {
    clearPanelTimers()
    setSelectedCourse(course)
    setPanelPhase('hidden')
    panelOpenFrameRef.current = window.requestAnimationFrame(() => {
      panelOpenFrameRef.current = window.requestAnimationFrame(() => {
        setPanelPhase('open')
        panelOpenFrameRef.current = null
      })
    })
  }

  function closeCoursePanel() {
    clearPanelTimers()
    setSelectedCourse(null)
    setPanelPhase('hidden')
  }

  async function openCourseDetails(node: Extract<GraphNode, { type: 'course' }>) {
    if (node.isAvailable === false) {
      showCoursePanel({
        code: node.code,
        title: 'Course unavailable',
        description: `${node.code} is a prerequisite for this course, but is not available in the current course catalog.`,
        catalogUrl: null,
        error: null,
      })
      return
    }

    if (node.courseId === graph?.rootCourse.id) {
      showCoursePanel({
        code: graph.rootCourse.code,
        title: graph.rootCourse.title,
        description: graph.rootCourse.description ?? 'No description available for this course.',
        catalogUrl: graph.rootCourse.catalogUrl ?? buildFallbackCatalogUrl(graph.rootCourse.code),
        error: null,
      })
      return
    }

    const fallbackCatalogUrl =
      node.courseId === graph?.rootCourse.id
        ? graph.rootCourse.catalogUrl
        : buildFallbackCatalogUrl(node.code)

    const currentRequestId = requestIdRef.current + 1
    requestIdRef.current = currentRequestId
    hideCoursePanelImmediately()

    try {
      const details = await fetchCourse(node.code)

      if (requestIdRef.current !== currentRequestId) {
        return
      }

      showCoursePanel({
        code: details.code,
        title: details.title,
        description: details.description ?? 'No description available for this course.',
        catalogUrl: details.catalogUrl ?? buildFallbackCatalogUrl(details.code),
        error: null,
      })
    } catch (unknownError) {
      if (requestIdRef.current !== currentRequestId) {
        return
      }

      const message =
        unknownError instanceof Error ? unknownError.message : 'Unable to load course details.'

      showCoursePanel({
        code: node.code,
        title: node.title,
        description:
          node.courseId === graph?.rootCourse.id
            ? graph.rootCourse.description ?? 'No description available for this course.'
            : 'Description unavailable for this course.',
        catalogUrl: fallbackCatalogUrl,
        error: message,
      })
    }
  }

  useEffect(() => {
    return () => {
      clearPanelTimers()
    }
  }, [])

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (event.target instanceof globalThis.Node && !helpRef.current?.contains(event.target)) {
        setShowHelp(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
    }
  }, [])

  useEffect(() => {
    if (!graph || !containerRef.current) {
      return
    }

    let destroyed = false
    const container = containerRef.current

    void document.fonts.ready.then(() => {
      if (destroyed || !container) return

      const isMobile =
        typeof window !== 'undefined' && window.matchMedia(MOBILE_GRAPH_QUERY).matches

      const renderGraph = graph

      const network = new Network(
        container,
        {
          nodes: new DataSet(toVisNodes(renderGraph)),
          edges: new DataSet(toVisEdges(renderGraph)),
        },
        getGraphOptions(isMobile),
      )

      networkRef.current = network

      network.once('afterDrawing', () => {
        network.fit({
          animation: isMobile
            ? false
            : {
                duration: 450,
                easingFunction: 'easeInOutQuad',
              },
        })
      })

      network.on('click', (event) => {
        const selectedNodeId = event.nodes[0]

        if (!selectedNodeId) {
          return
        }

        const node = graph.nodes.find((entry) => entry.id === selectedNodeId)

        if (!node || (node.type !== 'course' && node.type !== 'requirement')) {
          return
        }

        if (node.type === 'requirement') {
          showCoursePanel({
            code: 'Requirement',
            title: node.label,
            description: 'General requirement as outlined in the prerequisite data.',
            catalogUrl: null,
            error: null,
          })
          return
        }

        void openCourseDetails(node)
      })
    })

    return () => {
      destroyed = true
      if (networkRef.current) {
        networkRef.current.destroy()
        networkRef.current = null
      }
    }
  }, [graph])

  function zoomIn() {
    const network = networkRef.current

    if (!network) {
      return
    }

    network.moveTo({
      scale: network.getScale() * 1.4,
      animation: ZOOM_BUTTON_ANIMATION,
    })
  }

  function zoomOut() {
    const network = networkRef.current

    if (!network) {
      return
    }

    network.moveTo({
      scale: network.getScale() / 1.4,
      animation: ZOOM_BUTTON_ANIMATION,
    })
  }

  function resetView() {
    networkRef.current?.fit({
      animation: {
        duration: 350,
        easingFunction: 'easeInOutQuad',
      },
    })
  }

  return (
    <section className="graph-card">
      <div className="graph-surface-shell">
        {graph ? <div ref={containerRef} className="graph-network" /> : <div className="graph-empty-state" />}

        <div className="graph-actions">
          <button type="button" className="graph-action-button" onClick={zoomOut} aria-label="Zoom out">
            <span className="graph-action-icon graph-action-icon-minus" aria-hidden="true" />
          </button>
          <button type="button" className="graph-action-button" onClick={zoomIn} aria-label="Zoom in">
            <span className="graph-action-icon graph-action-icon-plus" aria-hidden="true" />
          </button>
          <button type="button" className="graph-action-button graph-action-button-reset" onClick={resetView}>
            Reset
          </button>
        </div>

        {!selectedCourse ? <p className="graph-selection-hint">Click on a course to see description</p> : null}

        <div
          ref={helpRef}
          className={`graph-help-control ${showHelp ? 'graph-help-control--overlay-open' : ''}`}
        >
          <div className="graph-help-legend-row">
            
            <div className={`graph-legend-drawer ${showLegend ? 'graph-legend-drawer--open' : ''}`}>
              <button
                type="button"
                className="graph-legend-tab"
                aria-expanded={showLegend}
                aria-controls="graph-legend-panel"
                onClick={() => setShowLegend((open) => !open)}
              >
                <span className="graph-legend-tab-label">Legend</span>
              </button>
              {showLegend ? (
                <aside id="graph-legend-panel" className="graph-legend" aria-label="Graph legend">
                  <div className="graph-legend-header">
                    <p className="graph-legend-title">Legend</p>
                  </div>
                  <div className="graph-legend-list">
                    <p className="graph-legend-item">
                      <span className="graph-legend-swatch graph-legend-swatch--red" aria-hidden="true" />
                      <span>All of</span>
                    </p>
                    <p className="graph-legend-item">
                      <span className="graph-legend-swatch graph-legend-swatch--blue" aria-hidden="true" />
                      <span>Any of</span>
                    </p>
                    <p className="graph-legend-item">
                      <span className="graph-legend-line graph-legend-line--solid" aria-hidden="true" />
                      <span>Prerequisite</span>
                    </p>
                    <p className="graph-legend-item">
                      <span className="graph-legend-line graph-legend-line--dotted" aria-hidden="true" />
                      <span>Corequisite</span>
                    </p>
                  </div>
                </aside>
              ) : null}
            </div>
            <button
              type="button"
              className="graph-help-button"
              aria-expanded={showHelp}
              aria-controls="graph-help-popover"
              onClick={() => setShowHelp((open) => !open)}
            >
              How to use?
            </button>
          </div>
          {showHelp ? (
            <section
              id="graph-help-popover"
              className="graph-help-popover"
              onClick={(event) => {
                if (event.target === event.currentTarget) {
                  setShowHelp(false)
                }
              }}
            >
              <div className="graph-help-popover-content">
                <button
                  type="button"
                  className="graph-help-popover-close"
                  onClick={() => setShowHelp(false)}
                  aria-label="Close help"
                  title="Close help"
                >
                  ×
                </button>
                <p>
                  Hello! This web app is a tool to simplify the process of searching for course
                  prerequisites at the University of Alberta through visualizing dependencies in a graph.
                  <br />
                  <br />
                  The graph can be utilized in two ways:
                  <br />
                  <br />
                  1. Prerequisite View:
                  <br />
                  Search any course to view its prerequisites (and corequisites). Clicking on a course
                  opens a popup to view its details and allow you to navigate directly to the course
                  catalogue page. The depth filter controls the level of courses that are displayed -
                  &apos;1 level&apos; means only the immediate prerequisites are displayed. Blue line
                  means that taking any of these courses will fulfill the requirement, while red line
                  means that all of those courses must be taken in order to fulfill the requirement.
                  Prerequisite courses are indicated with a solid line and corequisite courses are
                  indicated with a dotted line.
                  <br />
                  <br />
                  2. Dependency View:
                  <br />
                  Search any course to view all other courses that require having previously taken the
                  searched course. All courses displayed in red depend on the searched course at its root
                  as a prerequisite. This view is helpful as a tool to figure out the order in which
                  courses must be taken.
                  <br />
                  <br />
                  Note: This is a personal project and is not affiliated with the University of Alberta.
                  <br />
                  Data is sourced from the University of Alberta&apos;s course catalogue:
                  https://apps.ualberta.ca/catalogue/courses/
                  <br />
                </p>
                <a
                  href="https://github.com/judxyz/ua-prereq"
                  target="_blank"
                  rel="noreferrer"
                  className="graph-help-github-link"
                >
                  GitHub
                </a>
              </div>
            </section>
          ) : null}
        </div>

        {selectedCourse ? (
          <aside className={`course-panel course-panel--${panelPhase}`}>
            <div className="course-panel-header">
              <div>
                <h3>{getCoursePanelHeading(selectedCourse.code)}</h3>
              </div>
              <button
                type="button"
                className="course-panel-close"
                onClick={closeCoursePanel}
                aria-label="Close course details"
                title="Close"
              >
                ×
              </button>
            </div>
            <p className="course-panel-title">{selectedCourse.title}</p>
            {selectedCourse.catalogUrl ? (
              <a
                href={selectedCourse.catalogUrl}
                target="_blank"
                rel="noreferrer"
                className="course-panel-link"
              >
                Open in course catalogue
              </a>
            ) : null}
            <p className="course-panel-section-title">Description</p>
            <p className="course-panel-description">{selectedCourse.description}</p>
            {selectedCourse.error ? <p className="course-panel-error">{selectedCourse.error}</p> : null}
          </aside>
        ) : null}
      </div>
    </section>
  )
}
