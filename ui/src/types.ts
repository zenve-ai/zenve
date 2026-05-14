export interface User {
  id: string
  email: string
  name?: string
  createdAt?: string
}

export interface LoginData {
  email: string
  password: string
}

export interface SignupData {
  email: string
  password: string
  name?: string
}

/** Discriminator for Lucide icon mapping in the UI (Redux stays serializable). */
export type WorkspaceIconKey =
  | 'zap'
  | 'triangle'
  | 'box'
  | 'cpu'
  | 'building'
  | 'layers'

/** Agent list / detail icon (same pattern as `WorkspaceIconKey`). */
export type AgentIconKey = 'crown' | 'compass' | 'code'

export interface WorkspaceSummary {
  id: string
  name: string
  path: string
  registeredAt: string
  iconKey: WorkspaceIconKey
  agentCount: number
}

export interface WorkspaceDetail extends WorkspaceSummary {
  description: string
  defaultBranch: string
  runSchedule: string | null
  pipeline: Record<string, string | null>
  stack: string[]
  agents: string[]
  repo: string | null
}

/** Agent derived from workspace detail — runtime only exposes the slug list. */
export interface Agent {
  id: string
  workspaceId: string
  name: string
  slug: string
  adapterType: string
  model: string
  adapterConfig: Record<string, unknown>
  skills: string[]
  tools: string[]
  status: string
  enabled: boolean
  mode: string
  heartbeatIntervalSeconds: number
  lastHeartbeatAt: string | null
  createdAt: string
  updatedAt: string
}

export interface Run {
  id: string
  workspaceId: string
  agentId: string
  trigger: string
  status: string
  adapterType: string
  message: string | null
  startedAt: string | null
  finishedAt: string | null
  exitCode: number | null
  errorSummary: string | null
  tokenUsage: Record<string, unknown> | null
  transcriptPath: string | null
  outcome: string | null
  createdAt: string
}

export type RunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'timeout'

export type RunEventType = 'output' | 'tool_call' | 'tool_result' | 'error' | 'usage'

export interface RunEvent {
  id: string
  runId: string
  eventType: RunEventType
  content: string | null
  meta: Record<string, unknown> | null
  createdAt: string
}

export interface AgentUpdateBody {
  name?: string
  adapterConfig?: Record<string, unknown>
  skills?: string[]
  tools?: string[]
  status?: string
  heartbeatIntervalSeconds?: number
}

export interface RunCreateBody {
  agent: string
  message?: string | null
  adapterType?: string | null
  adapterConfig?: Record<string, unknown> | null
}

export interface AgentTemplate {
  id: string
  name: string
  description: string
}

export interface SkillTemplate {
  id: string
  name: string
  description: string
}

export interface AgentRun {
  runId: string
  agent: string
  startedAt: string
  finishedAt: string
  durationSeconds: number
  status: string
  exitCode: number
  item: { type: string; number: number; title: string } | null
  tokenUsage: { input_tokens: number; output_tokens: number; cost_usd: number | null } | null
  error: string | null
}

export interface AgentStats {
  agent: string
  totalRuns: number
  completedRuns: number
  failedRuns: number
  runs: AgentRun[]
}

export type RawRunEventType =
  | 'run.started' | 'run.completed' | 'run.failed' | 'run.committing'
  | 'agent.started' | 'agent.completed' | 'agent.failed'
  | 'agent.claimed_issue' | 'agent.claimed_pr' | 'agent.nothing_to_do'
  | 'agent.misconfigured' | 'agent.needs_input'
  | 'adapter.output' | 'adapter.tool_call' | 'adapter.tool_result'
  | 'adapter.usage' | 'adapter.error'
  | 'snapshot.fetched' | 'pipeline.transition' | 'pipeline.end'

export interface RawRunEvent {
  run_id: string
  timestamp: string
  type: RawRunEventType
  agent: string | null
  data: Record<string, unknown>
}
