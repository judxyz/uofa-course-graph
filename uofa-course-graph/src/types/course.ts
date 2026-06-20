export type CourseNumber = string | number

export type ParseStatus = 'parsed' | 'partial' | 'unparsed'

export interface CourseSearchItem {
  code: string
  title: string
}

export interface CourseSummary extends CourseSearchItem {
  id: number
  subject: string
  number: CourseNumber
  parseStatus: ParseStatus
}

export interface RootCourse extends CourseSummary {
  description: string | null
  otherNotes: string | null
  catalogUrl: string | null
}

export interface CourseDetails {
  id: number
  code: string
  title: string
  description: string | null
  otherNotes: string | null
  rawPrereqText: string | null
  rawCoreqText: string | null
  catalogUrl: string | null
  parseStatus: ParseStatus | null
}
