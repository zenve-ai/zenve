import { createApi } from '@reduxjs/toolkit/query/react'
import { createBaseQueryWithReauth } from '@/lib/api'
import config from '@/config'
import type { ProjectIconKey, ProjectSummary } from '@/types'

interface ProjectWithRoleResponse {
  id: string
  name: string
  slug: string
  created_at: string
  updated_at: string
  role: string
  github_repo: string | null
}

interface ProjectCreatedResponse extends ProjectWithRoleResponse {
  api_key: {
    id: string
    project_id: string
    name: string
    scopes: string
    is_active: boolean
    created_at: string
    expires_at: string | null
    raw_key: string
  }
}

const ICON_KEYS: ProjectIconKey[] = ['zap', 'triangle', 'box', 'cpu', 'building', 'layers']

function assignIconKey(slug: string): ProjectIconKey {
  let hash = 0
  for (let i = 0; i < slug.length; i++) {
    hash = (hash * 31 + slug.charCodeAt(i)) | 0
  }
  return ICON_KEYS[Math.abs(hash) % ICON_KEYS.length]
}

function toProjectSummary(p: ProjectWithRoleResponse): ProjectSummary {
  return {
    id: p.id,
    name: p.name,
    slug: p.slug,
    role: p.role,
    iconKey: assignIconKey(p.slug),
    githubRepo: p.github_repo ?? null,
  }
}

export const projectApi = createApi({
  reducerPath: 'projectApi',
  baseQuery: createBaseQueryWithReauth(config.apiUrl),
  tagTypes: ['Project'],
  endpoints: (builder) => ({
    listProjects: builder.query<ProjectSummary[], void>({
      query: () => '/projects',
      transformResponse: (response: ProjectWithRoleResponse[]) => response.map(toProjectSummary),
      providesTags: ['Project'],
    }),
    createProject: builder.mutation<ProjectSummary & { apiKey: string }, { name: string; slug?: string }>({
      query: (body) => ({ url: '/projects', method: 'POST', body }),
      transformResponse: (response: ProjectCreatedResponse) => ({
        ...toProjectSummary(response),
        apiKey: response.api_key.raw_key,
      }),
      invalidatesTags: ['Project'],
    }),
    connectGithub: builder.mutation<ProjectSummary, { projectId: string; installationId: number; repo: string }>({
      query: ({ projectId, installationId, repo }) => ({
        url: `/projects/${projectId}/github/connect`,
        method: 'POST',
        body: { installation_id: installationId, repo },
      }),
      transformResponse: (r: ProjectWithRoleResponse) => toProjectSummary(r),
      invalidatesTags: ['Project'],
    }),
    disconnectGithub: builder.mutation<void, { projectId: string }>({
      query: ({ projectId }) => ({ url: `/projects/${projectId}/github/disconnect`, method: 'DELETE' }),
      invalidatesTags: ['Project'],
    }),
  }),
})

export const {
  useListProjectsQuery,
  useCreateProjectMutation,
  useConnectGithubMutation,
  useDisconnectGithubMutation,
} = projectApi
