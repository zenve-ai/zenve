import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { ProjectSummary } from '@/types'
import { projectApi } from './api'

const STORAGE_KEY = 'zenve-current-project-id'
const LEGACY_STORAGE_KEY = 'zenve-current-org-id'

function readStoredProjectId(): string | null {
  try {
    const next = localStorage.getItem(STORAGE_KEY)
    if (next) return next
    const legacy = localStorage.getItem(LEGACY_STORAGE_KEY)
    if (legacy) {
      localStorage.setItem(STORAGE_KEY, legacy)
      localStorage.removeItem(LEGACY_STORAGE_KEY)
      return legacy
    }
  } catch {
    /* ignore */
  }
  return null
}

function writeStoredProjectId(id: string) {
  try {
    localStorage.setItem(STORAGE_KEY, id)
  } catch {
    /* ignore */
  }
}

export function resolveProjectId(
  projects: ProjectSummary[],
  candidate: string | null,
): string {
  if (!projects.length) return ''
  if (candidate && projects.some((p) => p.id === candidate)) return candidate
  return projects[0].id
}

export function resolveProjectFromSlug(
  projects: ProjectSummary[],
  slug: string | undefined,
): ProjectSummary | null {
  if (!slug) return null
  return projects.find((p) => p.slug === slug) ?? null
}

interface ProjectState {
  projects: ProjectSummary[]
  currentProjectId: string
  isInitialized: boolean
  listLoaded: boolean
}

const initialState: ProjectState = {
  projects: [],
  currentProjectId: '',
  isInitialized: false,
  listLoaded: false,
}

export const projectSlice = createSlice({
  name: 'project',
  initialState,
  reducers: {
    setCurrentProject: (state, action: PayloadAction<string>) => {
      const id = resolveProjectId(state.projects, action.payload)
      state.currentProjectId = id
      writeStoredProjectId(id)
    },
    restoreFromStorage: (state) => {
      const stored = readStoredProjectId()
      state.currentProjectId = stored ?? ''
      state.isInitialized = true
    },
  },
  extraReducers: (builder) => {
    builder.addMatcher(projectApi.endpoints.listProjects.matchFulfilled, (state, { payload }) => {
      state.projects = payload
      state.listLoaded = true
      const stored = state.currentProjectId || readStoredProjectId()
      const resolved = resolveProjectId(payload, stored)
      state.currentProjectId = resolved
      writeStoredProjectId(resolved)
    })
    builder.addMatcher(projectApi.endpoints.listProjects.matchRejected, (state) => {
      state.projects = []
      state.listLoaded = true
      state.currentProjectId = ''
      writeStoredProjectId('')
    })
  },
})

export const { setCurrentProject, restoreFromStorage } = projectSlice.actions

export const selectProjects = (state: { project: ProjectState }) => state.project.projects
export const selectCurrentProjectId = (state: { project: ProjectState }) =>
  state.project.currentProjectId
export const selectCurrentProject = (state: { project: ProjectState }) => {
  const { projects, currentProjectId } = state.project
  return projects.find((p) => p.id === currentProjectId) ?? projects[0] ?? null
}
export const selectIsProjectInitialized = (state: { project: ProjectState }) =>
  state.project.isInitialized
export const selectProjectListLoaded = (state: { project: ProjectState }) =>
  state.project.listLoaded

export default projectSlice.reducer
