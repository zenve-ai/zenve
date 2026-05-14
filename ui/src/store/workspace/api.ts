import { createApi } from '@reduxjs/toolkit/query/react'
import { createRuntimeBaseQuery } from '@/lib/api'
import config from '@/config'
import type { WorkspaceDetail, WorkspaceIconKey, WorkspaceSummary } from '@/types'

interface WorkspaceResponse {
  id: string
  path: string
  registered_at: string
}

interface WorkspaceDetailResponse extends WorkspaceResponse {
  project: string
  description: string
  default_branch: string
  run_schedule: string | null
  pipeline: Record<string, string | null>
  stack: string[]
  agents: string[]
  repo: string | null
}

const ICON_KEYS: WorkspaceIconKey[] = ['zap', 'triangle', 'box', 'cpu', 'building', 'layers']

function assignIconKey(seed: string): WorkspaceIconKey {
  let hash = 0
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) | 0
  }
  return ICON_KEYS[Math.abs(hash) % ICON_KEYS.length]
}

function nameFromPath(path: string): string {
  const trimmed = path.replace(/\/+$/, '')
  const parts = trimmed.split('/')
  return parts[parts.length - 1] || trimmed || path
}

function toWorkspaceSummary(w: WorkspaceResponse): WorkspaceSummary {
  return {
    id: w.id,
    name: nameFromPath(w.path),
    path: w.path,
    registeredAt: w.registered_at,
    iconKey: assignIconKey(w.id),
  }
}

function toWorkspaceDetail(w: WorkspaceDetailResponse): WorkspaceDetail {
  return {
    id: w.id,
    name: w.project || nameFromPath(w.path),
    path: w.path,
    registeredAt: w.registered_at,
    iconKey: assignIconKey(w.id),
    description: w.description,
    defaultBranch: w.default_branch,
    runSchedule: w.run_schedule,
    pipeline: w.pipeline,
    stack: w.stack,
    agents: w.agents,
    repo: w.repo,
  }
}

interface ScaffoldWorkspaceBody {
  name: string
  path: string
  description: string
  agents: string[]
}

export const workspaceApi = createApi({
  reducerPath: 'workspaceApi',
  baseQuery: createRuntimeBaseQuery(config.runtimeUrl),
  tagTypes: ['Workspace'],
  endpoints: (builder) => ({
    listWorkspaces: builder.query<WorkspaceSummary[], void>({
      query: () => '/workspaces',
      transformResponse: (response: WorkspaceResponse[]) => response.map(toWorkspaceSummary),
      providesTags: ['Workspace'],
    }),
    getWorkspace: builder.query<WorkspaceDetail, string>({
      query: (id) => `/workspaces/${id}`,
      transformResponse: (response: WorkspaceDetailResponse) => toWorkspaceDetail(response),
      providesTags: (_r, _e, id) => [{ type: 'Workspace', id }],
    }),
    registerWorkspace: builder.mutation<WorkspaceSummary, { path: string }>({
      query: (body) => ({ url: '/workspaces', method: 'POST', body }),
      transformResponse: (response: WorkspaceResponse) => toWorkspaceSummary(response),
      invalidatesTags: ['Workspace'],
    }),
    scaffoldWorkspace: builder.mutation<WorkspaceSummary, ScaffoldWorkspaceBody>({
      query: (body) => ({ url: '/workspaces/scaffold', method: 'POST', body }),
      transformResponse: (response: WorkspaceResponse) => toWorkspaceSummary(response),
      invalidatesTags: ['Workspace'],
    }),
    unregisterWorkspace: builder.mutation<void, string>({
      query: (id) => ({ url: `/workspaces/${id}`, method: 'DELETE' }),
      invalidatesTags: ['Workspace'],
    }),
  }),
})

export const {
  useListWorkspacesQuery,
  useGetWorkspaceQuery,
  useRegisterWorkspaceMutation,
  useScaffoldWorkspaceMutation,
  useUnregisterWorkspaceMutation,
} = workspaceApi
