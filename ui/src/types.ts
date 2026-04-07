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

export interface OrganizationSummary {
  id: string
  name: string
  slug: string
  role: string
  iconKey: OrganizationIconKey
}
