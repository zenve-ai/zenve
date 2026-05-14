import { createApi } from '@reduxjs/toolkit/query/react'
import { createRuntimeBaseQuery } from '@/lib/api'
import config from '@/config'
import type { Agent, AgentRun, AgentStats, AgentTemplate, AgentUpdateBody, SkillTemplate } from '@/types'

interface AgentSummaryResponse {
  slug: string
  name: string
  adapter_type: string
  model: string
  skills: string[]
  tools: string[]
  enabled: boolean
  mode: string
}

function summaryToAgent(workspaceId: string, s: AgentSummaryResponse): Agent {
  return {
    id: `${workspaceId}:${s.slug}`,
    workspaceId,
    name: s.name,
    slug: s.slug,
    adapterType: s.adapter_type,
    model: s.model,
    adapterConfig: {},
    skills: s.skills,
    tools: s.tools,
    enabled: s.enabled,
    mode: s.mode,
    status: s.enabled ? 'active' : 'archived',
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
      query: () => '/templates',
      transformResponse: (response: Array<{ id: string; name: string; description: string }>) =>
        response.map((t) => ({ id: t.id, name: t.name, description: t.description })),
    }),
    listSkills: builder.query<SkillTemplate[], void>({
      query: () => '/skills',
      transformResponse: (response: Array<{ id: string; name: string; description: string }>) =>
        response.map((s) => ({ id: s.id, name: s.name, description: s.description })),
    }),
    listAgents: builder.query<Agent[], { workspaceId: string }>({
      query: ({ workspaceId }) => `/workspaces/${workspaceId}/agents`,
      transformResponse: (response: AgentSummaryResponse[], _meta, arg) =>
        response.map((s) => summaryToAgent(arg.workspaceId, s)),
      providesTags: ['Agent'],
    }),
    getAgent: builder.query<Agent, { workspaceId: string; agentSlug: string }>({
      query: ({ workspaceId }) => `/workspaces/${workspaceId}/agents`,
      transformResponse: (response: AgentSummaryResponse[], _meta, arg) => {
        const summary = response.find((s) => s.slug === arg.agentSlug) ?? { slug: arg.agentSlug, name: arg.agentSlug }
        return summaryToAgent(arg.workspaceId, summary)
      },
      providesTags: (_r, _e, { agentSlug }) => [{ type: 'Agent', id: agentSlug }],
    }),
    getAgentStats: builder.query<AgentStats, { workspaceId: string; agentSlug: string }>({
      query: ({ workspaceId, agentSlug }) => `/workspaces/${workspaceId}/agents/${agentSlug}/stats`,
      transformResponse: (r: {
        agent: string
        total_runs: number
        completed_runs: number
        failed_runs: number
        runs: Array<{
          run_id: string
          agent: string
          started_at: string
          finished_at: string
          duration_seconds: number
          status: string
          exit_code: number
          item?: { type: string; number: number; title: string } | null
          token_usage?: { input_tokens: number; output_tokens: number; cost_usd: number | null } | null
          error?: string | null
        }>
      }): AgentStats => ({
        agent: r.agent,
        totalRuns: r.total_runs,
        completedRuns: r.completed_runs,
        failedRuns: r.failed_runs,
        runs: r.runs.map((run): AgentRun => ({
          runId: run.run_id,
          agent: run.agent,
          startedAt: run.started_at,
          finishedAt: run.finished_at,
          durationSeconds: run.duration_seconds,
          status: run.status,
          exitCode: run.exit_code,
          item: run.item ?? null,
          tokenUsage: run.token_usage ?? null,
          error: run.error ?? null,
        })),
      }),
      providesTags: (_r, _e, { workspaceId, agentSlug }) => [{ type: 'Agent', id: `${workspaceId}:${agentSlug}:stats` }],
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

export const { useListTemplatesQuery, useListSkillsQuery, useListAgentsQuery, useGetAgentQuery, useGetAgentStatsQuery, useUpdateAgentMutation } = agentsApi
