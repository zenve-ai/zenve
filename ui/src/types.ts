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
export type ProjectIconKey =
  | 'zap'
  | 'triangle'
  | 'box'
  | 'cpu'
  | 'building'
  | 'layers'

/** Agent list / detail icon (same pattern as `ProjectIconKey`). */
export type AgentIconKey = 'crown' | 'compass' | 'code'

export interface Agent {
  id: string
  projectId: string
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
  projectId: string
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

export interface GitHubRepo {
  id: number
  full_name: string
  name: string
  private: boolean
  default_branch: string
}

export interface ProjectSummary {
  id: string
  name: string
  slug: string
  role: string
  iconKey: ProjectIconKey
  githubRepo: string | null
}
