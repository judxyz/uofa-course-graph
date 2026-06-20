import type { CourseSummary, ParseStatus, RootCourse } from './course'

export type GroupType = 'ANY_OF' | 'ALL_OF' | 'COREQ' | 'UNKNOWN'
export type RelationType = 'PREREQ' | 'COREQ'
export type GraphViewMode = 'prereq' | 'dependency'
export type VisualStyle = string | null

export interface FetchCourseGraphOptions {
  maxDepth?: number
  includeCoreqs?: boolean
  viewMode?: GraphViewMode
}

export interface GraphMeta {
  maxDepth: number
  includeCoreqs: boolean
  viewMode?: GraphViewMode
}

export interface GraphGroup {
  id: number
  nodeId: string
  courseId: number
  groupType: GroupType
  parentGroupId: number | null
  displayLabel: string | null
  label: string
  visualStyle: VisualStyle
}

export interface GraphItemCourse extends Omit<CourseSummary, 'id' | 'subject' | 'number' | 'parseStatus'> {
  id: number | null
  subject: string | null
  number: string | number | null
  parseStatus: ParseStatus | null
  isAvailable?: boolean
  requirementText?: string | null
}

export interface GraphItem {
  id: number
  groupId: number
  requiredCourseId: number
  relationType: RelationType
  itemOrder: number | null
  course: GraphItemCourse
}

export interface BaseNode {
  id: string
  type: 'course' | 'group' | 'requirement'
  depth: number
}

export interface CourseNode extends BaseNode {
  type: 'course'
  courseId: number | null
  code: string
  subject: string
  number: string | number | null
  title: string
  parseStatus: ParseStatus | null
  isAvailable?: boolean
}

export interface GroupNode extends BaseNode {
  type: 'group'
  groupId: number
  groupType: GroupType
  label: string
  displayLabel: string | null
  visualStyle: VisualStyle
}

export interface RequirementNode extends BaseNode {
  type: 'requirement'
  requirementId: number
  label: string
}

export type GraphNode = CourseNode | GroupNode | RequirementNode

export interface GraphEdge {
  id: string
  source: string
  target: string
  relationType: RelationType
}

export interface GraphResponse {
  rootCourse: RootCourse
  groups: GraphGroup[]
  items: GraphItem[]
  nodes: GraphNode[]
  edges: GraphEdge[]
  rawPrerequisiteText: string | null
  rawCorequisiteText: string | null
  meta: GraphMeta
}
