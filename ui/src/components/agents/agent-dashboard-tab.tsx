import { ArrowRight, Check, Clock, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  MOCK_CHART_SUCCESS_RATE,
  MOCK_COST_ROWS,
  MOCK_COST_SUMMARY,
  MOCK_ISSUE_ROWS,
  type MockIssueRow,
} from '@/lib/mock-agent-dashboard'
import { useListRunsQuery } from '@/store/runs'
import type { Run } from '@/types'

// ─── helpers ────────────────────────────────────────────────────────────────

const OUTCOME_SIGNAL = /^(?:RUN_OK|RUN_FAILED|RUN_NEEDS_INPUT|HEARTBEAT_OK|HEARTBEAT_FAILED|HEARTBEAT_NEEDS_INPUT)(?::\s*(.+))?$/

function parseOutcome(outcome: string | null): string | null {
  if (!outcome) return null
  const lines = outcome.trim().split('\n').slice(-10).reverse()
  for (const raw of lines) {
    const line = raw.trim()
    const match = OUTCOME_SIGNAL.exec(line)
    if (match) return match[1]?.trim() ?? null
  }
  return null
}

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function formatDuration(startedAt: string | null, finishedAt: string | null): string {
  if (!startedAt || !finishedAt) return '—'
  const secs = Math.round((new Date(finishedAt).getTime() - new Date(startedAt).getTime()) / 1000)
  if (secs < 60) return `${secs}s`
  return `${Math.floor(secs / 60)}m ${secs % 60}s`
}

const RUN_STATUS: Record<string, { label: string; className: string }> = {
  completed: { label: 'DONE',    className: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' },
  running:   { label: 'RUN',     className: 'border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-400' },
  queued:    { label: 'QUEUED',  className: 'border-border text-muted-foreground' },
  failed:    { label: 'FAIL',    className: 'border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-400' },
  cancelled: { label: 'CANCEL', className: 'border-border text-muted-foreground' },
  timeout:   { label: 'TIMEOUT', className: 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400' },
}

// ─── sub-components ─────────────────────────────────────────────────────────

function SectionBar({ title, action }: { title: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-dashed border-border/60 bg-muted/20 px-3 py-1.5">
      <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{title}</span>
      {action}
    </div>
  )
}

function MiniBars({ values, barClassName }: { values: number[]; barClassName: string }) {
  const max = Math.max(...values, 1)
  return (
    <div className="flex h-24 items-end gap-px">
      {values.map((v, i) => (
        <div key={i} className="flex min-w-0 flex-1 flex-col justify-end">
          <div
            className={cn('w-full min-h-[2px] rounded-[1px]', barClassName)}
            style={{ height: `${(v / max) * 100}%` }}
          />
        </div>
      ))}
    </div>
  )
}

function IssueStatusBadge({ row }: { row: MockIssueRow }) {
  if (row.status === 'done') {
    return (
      <span className="border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] font-bold tracking-widest text-emerald-700 dark:text-emerald-400">
        DONE
      </span>
    )
  }
  if (row.status === 'in_progress') {
    return (
      <span className="border border-blue-500/40 bg-blue-500/10 px-2 py-0.5 font-mono text-[10px] font-bold tracking-widest text-blue-700 dark:text-blue-400">
        RUN
      </span>
    )
  }
  return (
    <span className="border border-border px-2 py-0.5 font-mono text-[10px] font-bold tracking-widest text-muted-foreground">
      OPEN
    </span>
  )
}

function RunRow({ run, onViewDetails }: { run: Run; onViewDetails?: () => void }) {
  const outcomeNote = parseOutcome(run.outcome)
  const duration = formatDuration(run.startedAt, run.finishedAt)
  const cfg = RUN_STATUS[run.status] ?? { label: run.status.toUpperCase(), className: 'border-border text-muted-foreground' }

  return (
    <div
      role={onViewDetails ? 'button' : undefined}
      tabIndex={onViewDetails ? 0 : undefined}
      onClick={onViewDetails}
      onKeyDown={onViewDetails ? (e) => { if (e.key === 'Enter') onViewDetails() } : undefined}
      className={cn(
        'flex min-w-0 items-center gap-2 px-3 py-2',
        onViewDetails && 'cursor-pointer hover:bg-accent/50',
      )}
    >
      <span className={cn('inline-flex shrink-0 items-center gap-0.5 border px-1 py-px font-mono text-[9px] font-bold tracking-widest', cfg.className)}>
        <Check className="size-2.5" />
        {cfg.label}
      </span>
      <span className="shrink-0 border border-border px-1 py-px font-mono text-[9px] tracking-widest text-muted-foreground uppercase">
        {run.trigger}
      </span>
      {duration !== '—' && (
        <span className="inline-flex shrink-0 items-center gap-0.5 border border-border px-1 py-px font-mono text-[9px] tracking-widest text-muted-foreground">
          <Clock className="size-2.5" />
          {duration}
        </span>
      )}
      <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-muted-foreground">
        {outcomeNote ?? run.errorSummary ?? run.id.slice(0, 8)}
      </span>
      <span className="shrink-0 font-mono text-[10px] text-muted-foreground/60">
        {formatRelativeTime(run.createdAt)}
      </span>
    </div>
  )
}

// ─── daily aggregation helpers ──────────────────────────────────────────────

interface DayGroup {
  label: string   // e.g. "14/Apr"
  dateKey: string // e.g. "2026-04-14"
  runs: Run[]
}

interface DayBucket {
  label: string
  dateKey: string
  value: number
}

function groupRunsByDay(runs: Run[], days = 7): DayGroup[] {
  const groups: DayGroup[] = []
  const nowMs = Date.now()
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(nowMs - i * 86_400_000)
    const dateKey = d.toISOString().slice(0, 10)
    const day = String(d.getUTCDate()).padStart(2, '0')
    const month = d.toLocaleDateString('en-US', { month: 'short', timeZone: 'UTC' })
    const label = `${day}/${month}`
    groups.push({ label, dateKey, runs: [] })
  }
  for (const run of runs) {
    const key = run.createdAt.slice(0, 10)
    const group = groups.find((g) => g.dateKey === key)
    if (group) group.runs.push(run)
  }
  return groups
}

function toBuckets(groups: DayGroup[], reducer: (runs: Run[]) => number): DayBucket[] {
  return groups.map((g) => ({ label: g.label, dateKey: g.dateKey, value: reducer(g.runs) }))
}

function getRunCostUsd(run: Run): number {
  const cost = (run.tokenUsage as { cost_usd?: unknown } | null)?.cost_usd
  return typeof cost === 'number' ? cost : 0
}

function DayBucketChart({
  buckets,
  barClassName,
  emptyLabel,
  formatValue,
}: {
  buckets: DayBucket[]
  barClassName: string
  emptyLabel: string
  formatValue?: (v: number) => string
}) {
  const hasData = buckets.some((b) => b.value > 0)
  if (!hasData) {
    return (
      <div className="flex h-24 flex-col items-center justify-center gap-1">
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground/50">{emptyLabel}</span>
      </div>
    )
  }
  const max = Math.max(...buckets.map((b) => b.value), 1)
  return (
    <div className="flex h-24 items-end gap-1">
      {buckets.map((b) => (
        <div
          key={b.dateKey}
          title={formatValue ? `${b.label}: ${formatValue(b.value)}` : `${b.label}: ${b.value}`}
          className="group relative flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-px"
        >
          <div
            className={cn('w-full min-h-[2px] rounded-[1px]', barClassName)}
            style={{ height: `${(b.value / max) * 100}%` }}
          />
          <span className="absolute -bottom-4 font-mono text-[9px] text-muted-foreground/60">{b.label}</span>
        </div>
      ))}
    </div>
  )
}

function formatUsd(v: number): string {
  if (v === 0) return '$0'
  if (v < 0.01) return `$${v.toFixed(4)}`
  if (v < 1) return `$${v.toFixed(3)}`
  return `$${v.toFixed(2)}`
}

// ─── main component ──────────────────────────────────────────────────────────

export function AgentDashboardTab({
  orgSlug,
  agentId,
  onViewRunDetails,
}: {
  orgSlug: string
  agentId: string
  onViewRunDetails?: () => void
}) {
  const { data: runs = [], isLoading: runsLoading } = useListRunsQuery(
    { orgSlug, agentId },
    { skip: !orgSlug || !agentId },
  )

  const renderRuns = () => (
    <section className="border border-border bg-card">
      <SectionBar
        title="Recent runs"
        action={
          <Button
            variant="ghost"
            size="xs"
            className="rounded-none text-[11px] font-normal text-muted-foreground hover:text-foreground"
            onClick={onViewRunDetails}
          >
            See all
            <ArrowRight className="size-3" />
          </Button>
        }
      />
      {runsLoading ? (
        <div className="flex items-center gap-2 px-3 py-3">
          <Loader2 className="size-3 animate-spin text-muted-foreground" />
          <span className="font-mono text-[10px] tracking-widest text-muted-foreground">LOADING...</span>
        </div>
      ) : runs.length === 0 ? (
        <p className="px-3 py-3 font-mono text-[11px] text-muted-foreground">No runs yet.</p>
      ) : (
        <ul className="divide-y divide-border/60">
          {[...runs].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()).slice(0, 5).map((run) => (
            <li key={run.id}>
              <RunRow run={run} onViewDetails={onViewRunDetails} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )

  const dayGroups = groupRunsByDay(runs)
  const runActivity = toBuckets(dayGroups, (rs) => rs.length)
  const runIssues = toBuckets(dayGroups, (rs) => rs.filter((r) => r.status === 'failed' || r.status === 'timeout').length)
  const runCost = toBuckets(dayGroups, (rs) => rs.reduce((sum, r) => sum + getRunCostUsd(r), 0))
  const hasRunActivity = runActivity.some((b) => b.value > 0)
  const hasRunIssues = runIssues.some((b) => b.value > 0)
  const hasRunCost = runCost.some((b) => b.value > 0)

  const renderCharts = () => (
    <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
      <div className="flex min-w-0 flex-col border border-border bg-card">
        <div className="border-b border-border/60 px-2 py-1.5">
          <p className="text-[12px] font-medium">Run activity</p>
          <p className="text-[10px] text-muted-foreground">Last 7 days</p>
        </div>
        <div className={cn('p-2', hasRunActivity && 'pb-5')}>
          <DayBucketChart buckets={runActivity} barClassName="bg-emerald-500/80" emptyLabel="No runs" />
        </div>
      </div>
      <div className="flex min-w-0 flex-col border border-border bg-card">
        <div className="border-b border-border/60 px-2 py-1.5">
          <p className="text-[12px] font-medium">Run issues</p>
          <p className="text-[10px] text-muted-foreground">Last 7 days</p>
        </div>
        <div className={cn('p-2', hasRunIssues && 'pb-5')}>
          <DayBucketChart buckets={runIssues} barClassName="bg-red-500/80" emptyLabel="No issues" />
        </div>
      </div>
      <div className="flex min-w-0 flex-col border border-border bg-card">
        <div className="border-b border-border/60 px-2 py-1.5">
          <p className="text-[12px] font-medium">Run cost</p>
          <p className="text-[10px] text-muted-foreground">Last 7 days</p>
        </div>
        <div className={cn('p-2', hasRunCost && 'pb-5')}>
          <DayBucketChart buckets={runCost} barClassName="bg-amber-500/80" emptyLabel="No cost" formatValue={formatUsd} />
        </div>
      </div>
      <div className="flex min-w-0 flex-col border border-border bg-card">
        <div className="border-b border-border/60 px-2 py-1.5">
          <p className="text-[12px] font-medium">Success rate</p>
          <p className="text-[10px] text-muted-foreground">Last 14 days</p>
        </div>
        <div className="p-2">
          <MiniBars values={MOCK_CHART_SUCCESS_RATE} barClassName="bg-emerald-500/85" />
        </div>
      </div>
    </div>
  )

  const renderIssues = () => (
    <section className="border border-border bg-card">
      <SectionBar
        title="Recent issues"
        action={
          <Button
            variant="ghost"
            size="xs"
            className="rounded-none text-[11px] font-normal text-muted-foreground hover:text-foreground"
          >
            See all
            <ArrowRight className="size-3" />
          </Button>
        }
      />
      <ul className="divide-y divide-border/60">
        {MOCK_ISSUE_ROWS.map((row) => (
          <li key={row.id} className="flex items-start gap-3 px-3 py-2">
            <span className="shrink-0 font-mono text-[10px] text-muted-foreground">{row.id}</span>
            <span className="min-w-0 flex-1 text-[12px] leading-snug">{row.title}</span>
            <IssueStatusBadge row={row} />
          </li>
        ))}
      </ul>
    </section>
  )

  const renderCosts = () => (
    <section className="border border-border bg-card">
      <SectionBar title="Costs (mock)" />
      <div className="grid gap-3 border-b border-dashed border-border/60 px-3 py-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Input tokens</p>
          <p className="font-mono text-[13px]">{MOCK_COST_SUMMARY.inputTokens}</p>
        </div>
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Output tokens</p>
          <p className="font-mono text-[13px]">{MOCK_COST_SUMMARY.outputTokens}</p>
        </div>
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Cached tokens</p>
          <p className="font-mono text-[13px]">{MOCK_COST_SUMMARY.cachedTokens}</p>
        </div>
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Total cost</p>
          <p className="font-mono text-[13px]">{MOCK_COST_SUMMARY.totalCost}</p>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-left text-[12px]">
          <thead>
            <tr className="border-b border-border/60 bg-muted/15 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              <th className="px-3 py-2 font-medium">Date</th>
              <th className="px-3 py-2 font-medium">Run</th>
              <th className="px-3 py-2 font-medium">Input</th>
              <th className="px-3 py-2 font-medium">Output</th>
              <th className="px-3 py-2 font-medium">Cost</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_COST_ROWS.map((row) => (
              <tr key={row.runId} className="border-b border-border/40 font-mono">
                <td className="px-3 py-2 text-[11px]">{row.date}</td>
                <td className="px-3 py-2 text-[11px] text-muted-foreground">{row.runId}</td>
                <td className="px-3 py-2">{row.input}</td>
                <td className="px-3 py-2">{row.output}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.cost}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )

  return (
    <div className="flex flex-col gap-4 p-4">
      {renderRuns()}
      {renderCharts()}
      {renderIssues()}
      {renderCosts()}
    </div>
  )
}
