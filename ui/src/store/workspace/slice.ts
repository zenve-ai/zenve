import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { WorkspaceSummary } from '@/types'
import { workspaceApi } from './api'

const STORAGE_KEY = 'zenve-current-workspace-id'

function readStoredWorkspaceId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function writeStoredWorkspaceId(id: string) {
  try {
    localStorage.setItem(STORAGE_KEY, id)
  } catch {
    /* ignore */
  }
}

export function resolveWorkspaceId(
  workspaces: WorkspaceSummary[],
  candidate: string | null,
): string {
  if (!workspaces.length) return ''
  if (candidate && workspaces.some((w) => w.id === candidate)) return candidate
  return workspaces[0].id
}

export function resolveWorkspaceFromId(
  workspaces: WorkspaceSummary[],
  id: string | undefined,
): WorkspaceSummary | null {
  if (!id) return null
  return workspaces.find((w) => w.id === id) ?? null
}

interface WorkspaceState {
  workspaces: WorkspaceSummary[]
  currentWorkspaceId: string
  isInitialized: boolean
  listLoaded: boolean
}

const initialState: WorkspaceState = {
  workspaces: [],
  currentWorkspaceId: '',
  isInitialized: false,
  listLoaded: false,
}

export const workspaceSlice = createSlice({
  name: 'workspace',
  initialState,
  reducers: {
    setCurrentWorkspace: (state, action: PayloadAction<string>) => {
      const id = resolveWorkspaceId(state.workspaces, action.payload)
      state.currentWorkspaceId = id
      writeStoredWorkspaceId(id)
    },
    restoreFromStorage: (state) => {
      const stored = readStoredWorkspaceId()
      state.currentWorkspaceId = stored ?? ''
      state.isInitialized = true
    },
  },
  extraReducers: (builder) => {
    builder.addMatcher(workspaceApi.endpoints.listWorkspaces.matchFulfilled, (state, { payload }) => {
      state.workspaces = payload
      state.listLoaded = true
      const stored = state.currentWorkspaceId || readStoredWorkspaceId()
      const resolved = resolveWorkspaceId(payload, stored)
      state.currentWorkspaceId = resolved
      writeStoredWorkspaceId(resolved)
    })
    builder.addMatcher(workspaceApi.endpoints.listWorkspaces.matchRejected, (state) => {
      state.workspaces = []
      state.listLoaded = true
      state.currentWorkspaceId = ''
      writeStoredWorkspaceId('')
    })
  },
})

export const { setCurrentWorkspace, restoreFromStorage } = workspaceSlice.actions

export const selectWorkspaces = (state: { workspace: WorkspaceState }) => state.workspace.workspaces
export const selectCurrentWorkspaceId = (state: { workspace: WorkspaceState }) =>
  state.workspace.currentWorkspaceId
export const selectCurrentWorkspace = (state: { workspace: WorkspaceState }) => {
  const { workspaces, currentWorkspaceId } = state.workspace
  return workspaces.find((w) => w.id === currentWorkspaceId) ?? workspaces[0] ?? null
}
export const selectIsWorkspaceInitialized = (state: { workspace: WorkspaceState }) =>
  state.workspace.isInitialized
export const selectWorkspaceListLoaded = (state: { workspace: WorkspaceState }) =>
  state.workspace.listLoaded

export default workspaceSlice.reducer
