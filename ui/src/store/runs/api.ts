import { createApi } from '@reduxjs/toolkit/query/react'
import { createBaseQueryWithReauth } from '@/lib/api'
import config from '@/config'
import type { Run, RunCreateBody, RunEvent } from '@/types'

interface RunResponse {
  id: string
  project_id?: string
  org_id?: string
  agent_id: string
  trigger: string
  status: string
  adapter_type: string
  message: string | null
  started_at: string | null
  finished_at: string | null
  exit_code: number | null
  error_summary: string | null
  token_usage: Record<string, unknown> | null
  transcript_path: string | null
  outcome: string | null
  created_at: string
}

interface RunEventResponse {
  id: string
  run_id: string
  event_type: string
  content: string | null
  meta: Record<string, unknown> | null
  created_at: string
}

function toRunEvent(r: RunEventResponse): RunEvent {
  return {
    id: r.id,
    runId: r.run_id,
    eventType: r.event_type as RunEvent['eventType'],
    content: r.content,
    meta: r.meta,
    createdAt: r.created_at,
  }
}

function toRun(r: RunResponse): Run {
  return {
    id: r.id,
    projectId: r.project_id ?? r.org_id ?? '',
    agentId: r.agent_id,
    trigger: r.trigger,
    status: r.status,
    adapterType: r.adapter_type,
    message: r.message,
    startedAt: r.started_at,
    finishedAt: r.finished_at,
    exitCode: r.exit_code,
    errorSummary: r.error_summary,
    tokenUsage: r.token_usage,
    transcriptPath: r.transcript_path,
    outcome: r.outcome,
    createdAt: r.created_at,
  }
}

export const runsApi = createApi({
  reducerPath: 'runsApi',
  baseQuery: createBaseQueryWithReauth(config.apiUrl),
  tagTypes: ['Run'],
  endpoints: (builder) => ({
    listRuns: builder.query<Run[], { projectSlug: string; agentId?: string; status?: string }>({
      query: ({ projectSlug, agentId, status }) => {
        const params = new URLSearchParams()
        if (agentId) params.set('agent_id', agentId)
        if (status) params.set('status', status)
        const qs = params.toString()
        return `/v1/projects/${projectSlug}/runs${qs ? `?${qs}` : ''}`
      },
      transformResponse: (response: RunResponse[]) => response.map(toRun),
      providesTags: ['Run'],
    }),
    getRun: builder.query<Run, { projectSlug: string; runId: string }>({
      query: ({ projectSlug, runId }) => `/v1/projects/${projectSlug}/runs/${runId}`,
      transformResponse: (response: RunResponse) => toRun(response),
      providesTags: (_result, _err, { runId }) => [{ type: 'Run', id: runId }],
    }),
    createRun: builder.mutation<Run, { projectSlug: string; body: RunCreateBody }>({
      query: ({ projectSlug, body }) => ({
        url: `/v1/projects/${projectSlug}/runs`,
        method: 'POST',
        body,
      }),
      transformResponse: (response: RunResponse) => toRun(response),
    }),
    getRunEvents: builder.query<RunEvent[], { projectSlug: string; runId: string }>({
      query: ({ projectSlug, runId }) => `/v1/projects/${projectSlug}/runs/${runId}/events`,
      transformResponse: (response: RunEventResponse[]) => response.map(toRunEvent),
    }),
  }),
})

export const {
  useListRunsQuery,
  useGetRunQuery,
  useCreateRunMutation,
  useGetRunEventsQuery,
} = runsApi
