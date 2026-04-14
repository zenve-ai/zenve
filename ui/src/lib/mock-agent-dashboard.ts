/** Fixture data for agent dashboard until analytics/issues APIs exist. */

export interface MockLatestRun {
  statusLabel: string
  statusVariant: 'success' | 'warning' | 'destructive' | 'muted'
  runIdShort: string
  triggerLabel: string
  relativeTime: string
}

export interface MockIssueRow {
  id: string
  title: string
  status: 'done' | 'open' | 'in_progress'
  /** Issue creation time (ISO), used for daily charts and sorting. */
  createdAt: string
}

function utcNoonIsoDaysAgo(daysAgo: number): string {
  const d = new Date(Date.now() - daysAgo * 86_400_000)
  d.setUTCHours(12, 0, 0, 0)
  return d.toISOString()
}

export interface MockCostRow {
  date: string
  runId: string
  input: string
  output: string
  cost: string
}

export interface MockCostSummary {
  inputTokens: string
  outputTokens: string
  cachedTokens: string
  totalCost: string
}

/** Normalized bar heights 0–100 for 14 days. */
export const MOCK_CHART_RUN_ACTIVITY: number[] = [
  35, 52, 28, 61, 44, 70, 33, 48, 55, 40, 66, 38, 58, 45,
]

/** Stacked contribution per day (critical, high, medium, low) — arbitrary positive numbers. */
export const MOCK_CHART_ISSUES_PRIORITY_DAYS: [number, number, number, number][] = [
  [2, 4, 8, 12],
  [1, 3, 6, 10],
  [3, 5, 7, 9],
  [0, 2, 5, 14],
  [2, 6, 8, 11],
  [1, 4, 7, 13],
  [2, 3, 6, 12],
  [4, 5, 8, 10],
  [1, 2, 5, 15],
  [2, 5, 9, 11],
  [3, 4, 7, 12],
  [1, 3, 8, 14],
  [2, 4, 6, 13],
  [1, 5, 7, 10],
]

export const MOCK_ISSUES_PRIORITY_LEGEND = [
  { key: 'critical', label: 'Critical', className: 'bg-red-500' },
  { key: 'high', label: 'High', className: 'bg-orange-500' },
  { key: 'medium', label: 'Medium', className: 'bg-blue-500' },
  { key: 'low', label: 'Low', className: 'bg-muted-foreground/50' },
] as const

export const MOCK_CHART_ISSUES_STATUS: number[] = [
  42, 38, 45, 50, 48, 55, 40, 52, 47, 44, 49, 51, 46, 53,
]

export const MOCK_LATEST_RUN: MockLatestRun = {
  statusLabel: 'succeeded',
  statusVariant: 'success',
  runIdShort: '460241e3',
  triggerLabel: 'Timer',
  relativeTime: '5d ago',
}

export const MOCK_ISSUE_ROWS: MockIssueRow[] = [
  { id: 'LOG-16', title: 'Verify rate limits on public signup endpoint.', status: 'open', createdAt: utcNoonIsoDaysAgo(0) },
  { id: 'LOG-15', title: 'Tighten copy for session expiry modal.', status: 'in_progress', createdAt: utcNoonIsoDaysAgo(0) },
  { id: 'LOG-12', title: 'Define account creation requirements and edge cases.', status: 'done', createdAt: utcNoonIsoDaysAgo(0) },
  { id: 'LOG-11', title: 'Review API error format with backend team.', status: 'done', createdAt: utcNoonIsoDaysAgo(1) },
  { id: 'LOG-14', title: 'Add telemetry for failed login reasons.', status: 'done', createdAt: utcNoonIsoDaysAgo(1) },
  { id: 'LOG-10', title: 'Draft acceptance criteria for onboarding flow.', status: 'in_progress', createdAt: utcNoonIsoDaysAgo(2) },
  { id: 'LOG-13', title: 'Document webhook retry policy.', status: 'done', createdAt: utcNoonIsoDaysAgo(2) },
  { id: 'LOG-09', title: 'Sync with design on empty states.', status: 'open', createdAt: utcNoonIsoDaysAgo(3) },
  { id: 'LOG-08', title: 'List edge cases for org invite flow.', status: 'done', createdAt: utcNoonIsoDaysAgo(3) },
  { id: 'LOG-07', title: 'Align on audit log retention.', status: 'done', createdAt: utcNoonIsoDaysAgo(4) },
  { id: 'LOG-06', title: 'Spike: export run history as CSV.', status: 'done', createdAt: utcNoonIsoDaysAgo(4) },
  // { id: 'LOG-05', title: 'Clarify RBAC matrix for agent roles.', status: 'done', createdAt: utcNoonIsoDaysAgo(5) },
  // { id: 'LOG-04', title: 'Capture screenshots for operator manual.', status: 'open', createdAt: utcNoonIsoDaysAgo(6) },
]

export const MOCK_COST_SUMMARY: MockCostSummary = {
  inputTokens: '3.1M',
  outputTokens: '21.2k',
  cachedTokens: '2.1M',
  totalCost: '$0.00',
}

export const MOCK_COST_ROWS: MockCostRow[] = [
  { date: 'Apr 7, 2026', runId: 'a1b2c3d4', input: '80.3k', output: '1.2k', cost: '—' },
  { date: 'Apr 6, 2026', runId: 'e5f67890', input: '62.1k', output: '980', cost: '—' },
  { date: 'Apr 5, 2026', runId: 'ab12cd34', input: '71.4k', output: '1.1k', cost: '—' },
]
