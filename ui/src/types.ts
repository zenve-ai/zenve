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
export type OrganizationIconKey =
  | 'zap'
  | 'triangle'
  | 'box'
  | 'cpu'
  | 'building'
  | 'layers'

/** Agent list / detail icon (same pattern as `OrganizationIconKey`). */
export type AgentIconKey = 'crown' | 'compass' | 'code'

export interface Agent {
  id: string
  orgId: string
  name: string
  slug: string
  adapterType: string
  adapterConfig: Record<string, unknown>
  skills: string[]
  status: string
  heartbeatIntervalSeconds: number
  lastHeartbeatAt: string | null
  createdAt: string
  updatedAt: string
}

export interface OrganizationSummary {
  id: string
  name: string
  slug: string
  role: string
  iconKey: OrganizationIconKey
}
