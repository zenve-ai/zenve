import { createApi } from '@reduxjs/toolkit/query/react'
import { createBaseQueryWithReauth } from '@/lib/api'
import config from '@/config'
import type { Agent } from '@/types'

interface AgentResponse {
  id: string
  org_id: string
  name: string
  slug: string
  dir_path: string
  adapter_type: string
  adapter_config: Record<string, unknown>
  skills: string[]
  status: string
  heartbeat_interval_seconds: number
  last_heartbeat_at: string | null
  created_at: string
  updated_at: string
}

function toAgent(r: AgentResponse): Agent {
  return {
    id: r.id,
    orgId: r.org_id,
    name: r.name,
    slug: r.slug,
    adapterType: r.adapter_type,
    adapterConfig: r.adapter_config,
    skills: r.skills,
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
    listAgents: builder.query<Agent[], { orgSlug: string }>({
      query: ({ orgSlug }) => `/orgs/${orgSlug}/agents`,
      transformResponse: (response: AgentResponse[]) => response.map(toAgent),
      providesTags: ['Agent'],
    }),
  }),
})

export const { useListAgentsQuery } = agentsApi
