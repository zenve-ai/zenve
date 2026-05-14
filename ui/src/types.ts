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
  adapterConfig: Record<string, unknown>
  skills: string[]
  tools: string[]
  status: string
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
