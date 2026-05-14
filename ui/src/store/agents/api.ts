import { createApi } from '@reduxjs/toolkit/query/react'
import { createRuntimeBaseQuery } from '@/lib/api'
import config from '@/config'
import type { Agent, AgentTemplate, AgentUpdateBody } from '@/types'

interface WorkspaceDetailResponse {
  id: string
  agents: string[]
}

function slugToAgent(workspaceId: string, slug: string): Agent {
  return {
    id: `${workspaceId}:${slug}`,
    workspaceId,
    name: slug,
    slug,
    adapterType: '',
    adapterConfig: {},
    skills: [],
    tools: [],
    status: 'active',
    heartbeatIntervalSeconds: 0,
    lastHeartbeatAt: null,
    createdAt: '',
    updatedAt: '',
  }
}

export const agentsApi = createApi({
  reducerPath: 'agentsApi',
  baseQuery: createRuntimeBaseQuery(config.runtimeUrl),
  tagTypes: ['Agent'],
  endpoints: (builder) => ({
    listTemplates: builder.query<AgentTemplate[], void>({
      queryFn: () => ({ data: [] }),
    }),
    listAgents: builder.query<Agent[], { workspaceId: string }>({
      query: ({ workspaceId }) => `/workspaces/${workspaceId}`,
      transformResponse: (response: WorkspaceDetailResponse) =>
        response.agents.map((slug) => slugToAgent(response.id, slug)),
      providesTags: ['Agent'],
    }),
    getAgent: builder.query<Agent, { workspaceId: string; agentSlug: string }>({
      query: ({ workspaceId }) => `/workspaces/${workspaceId}`,
      transformResponse: (response: WorkspaceDetailResponse, _meta, arg) => {
        const slug = response.agents.find((s) => s === arg.agentSlug)
        return slugToAgent(response.id, slug ?? arg.agentSlug)
      },
      providesTags: (_r, _e, { agentSlug }) => [{ type: 'Agent', id: agentSlug }],
    }),
    updateAgent: builder.mutation<
      Agent,
      { workspaceId: string; agentIdOrSlug: string; body: AgentUpdateBody }
    >({
      queryFn: ({ workspaceId, agentIdOrSlug }) => ({
        data: slugToAgent(workspaceId, agentIdOrSlug),
      }),
    }),
  }),
})

export const { useListTemplatesQuery, useListAgentsQuery, useGetAgentQuery, useUpdateAgentMutation } = agentsApi
