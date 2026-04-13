import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { AppRootState } from '@/store/index'
import type { Run, RunEvent } from '@/types'
import { runsApi } from './api'

interface RunsState {
  patches: Record<string, Partial<Run>>
  eventsByRunId: Record<string, RunEvent[]>
}

const initialState: RunsState = {
  patches: {},
  eventsByRunId: {},
}

export const runsSlice = createSlice({
  name: 'runs',
  initialState,
  reducers: {
    runCreated: (state, action: PayloadAction<Run>) => {
      state.patches[action.payload.id] = action.payload
    },
    runStatusChanged: (
      state,
      action: PayloadAction<{ run_id: string; status: string; started_at: string | null }>,
    ) => {
      const { run_id, status, started_at } = action.payload
      state.patches[run_id] = { ...state.patches[run_id], status, startedAt: started_at }
    },
    runEventReceived: (state, action: PayloadAction<RunEvent>) => {
      const { runId } = action.payload
      if (!state.eventsByRunId[runId]) {
        state.eventsByRunId[runId] = []
      }
      state.eventsByRunId[runId].push(action.payload)
    },
    runFinished: (
      state,
      action: PayloadAction<{
        run_id: string
        status: string
        outcome: string | null
        finished_at: string
      }>,
    ) => {
      const { run_id, status, outcome, finished_at } = action.payload
      state.patches[run_id] = { ...state.patches[run_id], status, outcome, finishedAt: finished_at }
    },
  },
})

export const { runCreated, runStatusChanged, runEventReceived, runFinished } = runsSlice.actions

export const selectRuns = (orgSlug: string) => (state: AppRootState): Run[] => {
  const { data: runs = [] } = runsApi.endpoints.listRuns.select({ orgSlug })(state)
  const { patches } = state.runs
  return runs.map((run) => ({ ...run, ...patches[run.id] }))
}

export const selectRunById = (orgSlug: string, runId: string) => (state: AppRootState): Run | undefined => {
  const runs = selectRuns(orgSlug)(state)
  return runs.find((r) => r.id === runId)
}

export const selectRunEventsByRunId = (runId: string) => (state: AppRootState): RunEvent[] =>
  state.runs.eventsByRunId[runId] ?? []

export default runsSlice.reducer
