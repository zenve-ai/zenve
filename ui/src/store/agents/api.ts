import { createApi } from '@reduxjs/toolkit/query/react'
import { createBaseQueryWithReauth } from '@/lib/api'
import config from '@/config'
import type { Agent, AgentUpdateBody } from '@/types'

interface AgentResponse {
  id: string
  project_id?: string
  org_id?: string
  name: string
  slug: string
  dir_path: string
  adapter_type: string
  adapter_config: Record<string, unknown>
  skills: string[]
  tools?: string[]
  status: string
  heartbeat_interval_seconds: number
  last_heartbeat_at: string | null
  created_at: string
  updated_at: string
}

function toAgent(r: AgentResponse): Agent {
  return {
    id: r.id,
    projectId: r.project_id ?? r.org_id ?? '',
    name: r.name,
    slug: r.slug,
    adapterType: r.adapter_type,
    adapterConfig: r.adapter_config,
    skills: r.skills,
    tools: r.tools ?? [],
    status: r.status,
    heartbeatIntervalSeconds: r.heartbeat_interval_seconds,
    lastHeartbeatAt: r.last_heartbeat_at,
    createdAt: r.created_at,
    updatedAt: r.updated_at,
  }
}

export const agentsApi = createApi({
  reducerPath: 'agentsApi',
  baseQuery: createBaseQueryWithReauth(config.apiUrl),
  tagTypes: ['Agent'],
  endpoints: (builder) => ({
    listAgents: builder.query<Agent[], { projectSlug: string }>({
      query: ({ projectSlug }) => `/projects/${projectSlug}/agents`,
      transformResponse: (response: AgentResponse[]) => response.map(toAgent),
      providesTags: ['Agent'],
    }),
    getAgent: builder.query<Agent, { projectSlug: string; agentSlug: string }>({
      query: ({ projectSlug, agentSlug }) => `/projects/${projectSlug}/agents/${agentSlug}`,
      transformResponse: (response: AgentResponse) => toAgent(response),
      providesTags: (_result, _err, { agentSlug }) => [{ type: 'Agent', id: agentSlug }],
    }),
    updateAgent: builder.mutation<
      Agent,
      { projectSlug: string; agentIdOrSlug: string; body: AgentUpdateBody }
    >({
      query: ({ projectSlug, agentIdOrSlug, body }) => ({
        url: `/projects/${projectSlug}/agents/${agentIdOrSlug}`,
        method: 'PATCH',
        body,
      }),
      transformResponse: (response: AgentResponse) => toAgent(response),
      invalidatesTags: (_result, _err, { agentIdOrSlug }) => [
        'Agent',
        { type: 'Agent', id: agentIdOrSlug },
      ],
    }),
  }),
})

export const { useListAgentsQuery, useGetAgentQuery, useUpdateAgentMutation } = agentsApi
