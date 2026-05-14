import { createApi } from '@reduxjs/toolkit/query/react'
import { createRuntimeBaseQuery } from '@/lib/api'
import config from '@/config'
import type { RawRunEvent, Run, RunCreateBody } from '@/types'

interface WorkspaceRunSummaryResponse {
  run_id: string
  agent: string
  started_at: string
  finished_at: string
  duration_seconds: number
  status: string
  exit_code: number
}

interface WorkspaceRunResponse {
  run_id: string
  started_at: string
  finished_at: string
  status: string
  agents: WorkspaceRunSummaryResponse[]
}

interface WorkspaceRunDetailResponse extends WorkspaceRunSummaryResponse {
  item?: { type: string; number: number; title: string } | null
  output?: string | null
  pipeline_transition?: { from_label: string; to_label: string[] | null } | null
  token_usage?: { input_tokens: number; output_tokens: number; cost_usd: number | null } | null
  error?: string | null
}

interface RunTriggerResponse {
  run_id: string
  status: string
}

function flatten(workspaceId: string, runs: WorkspaceRunResponse[]): Run[] {
  const out: Run[] = []
  for (const wr of runs) {
    for (const agent of wr.agents) {
      out.push({
        id: `${wr.run_id}:${agent.agent}`,
        workspaceId,
        agentId: agent.agent,
        trigger: 'manual',
        status: agent.status,
        adapterType: '',
        message: null,
        startedAt: agent.started_at || null,
        finishedAt: agent.finished_at || null,
        exitCode: agent.exit_code,
        errorSummary: null,
        tokenUsage: null,
        transcriptPath: null,
        outcome: null,
        createdAt: agent.started_at || wr.started_at || '',
      })
    }
  }
  return out
}

function detailToRun(workspaceId: string, d: WorkspaceRunDetailResponse): Run {
  return {
    id: `${d.run_id}:${d.agent}`,
    workspaceId,
    agentId: d.agent,
    trigger: 'manual',
    status: d.status,
    adapterType: '',
    message: null,
    startedAt: d.started_at || null,
    finishedAt: d.finished_at || null,
    exitCode: d.exit_code,
    errorSummary: d.error ?? null,
    tokenUsage: d.token_usage
      ? {
          input_tokens: d.token_usage.input_tokens,
          output_tokens: d.token_usage.output_tokens,
          cost_usd: d.token_usage.cost_usd,
        }
      : null,
    transcriptPath: null,
    outcome: d.output ?? null,
    createdAt: d.started_at || '',
  }
}

export const runsApi = createApi({
  reducerPath: 'runsApi',
  baseQuery: createRuntimeBaseQuery(config.runtimeUrl),
  tagTypes: ['Run'],
  endpoints: (builder) => ({
    listRuns: builder.query<Run[], { workspaceId: string; agentId?: string; status?: string }>({
      query: ({ workspaceId }) => `/workspaces/${workspaceId}/runs`,
      transformResponse: (response: WorkspaceRunResponse[], _meta, arg) => {
        const flat = flatten(arg.workspaceId, response)
        return flat.filter((r) => {
          if (arg.agentId && r.agentId !== arg.agentId) return false
          if (arg.status && r.status !== arg.status) return false
          return true
        })
      },
      providesTags: ['Run'],
    }),
    getRun: builder.query<Run, { workspaceId: string; runId: string }>({
      query: ({ workspaceId, runId }) => `/workspaces/${workspaceId}/runs/${runId}`,
      transformResponse: (response: WorkspaceRunDetailResponse, _meta, arg) =>
        detailToRun(arg.workspaceId, response),
      providesTags: (_r, _e, { runId }) => [{ type: 'Run', id: runId }],
    }),
    createRun: builder.mutation<
      { runId: string; status: string },
      { workspaceId: string; body: RunCreateBody }
    >({
      query: ({ workspaceId, body }) => ({
        url: `/workspaces/${workspaceId}/runs`,
        method: 'POST',
        body: { only_agent: body.agent ?? null },
      }),
      transformResponse: (response: RunTriggerResponse) => ({
        runId: response.run_id,
        status: response.status,
      }),
      invalidatesTags: ['Run'],
    }),
    getRunEvents: builder.query<RawRunEvent[], { workspaceId: string; runId: string }>({
      query: ({ workspaceId, runId }) => `/workspaces/${workspaceId}/runs/${runId}/events`,
    }),
    getActiveRun: builder.query<{ run_id: string; status: string } | null, { workspaceId: string }>({
      query: ({ workspaceId }) => `/workspaces/${workspaceId}/runs/active-run`,
      providesTags: ['Run'],
    }),
  }),
})

export const {
  useListRunsQuery,
  useGetRunQuery,
  useCreateRunMutation,
  useGetRunEventsQuery,
  useGetActiveRunQuery,
} = runsApi
