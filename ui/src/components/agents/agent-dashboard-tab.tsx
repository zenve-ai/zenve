import { useState } from 'react'
import { ArrowRight, Check, Clock, Loader2 } from 'lucide-react'
import { AgentDashboardBarChartCard } from '@/components/agents/agent-dashboard-bar-chart-card'
import { RunLogView } from '@/components/runs'
import { Button } from '@/components/ui/button'
import type { ChartConfig } from '@/components/ui/chart'
import {
  buildDayGroupsForLastNDays,
  type DayBucket,
  type DayGroup,
  timestampToLocalCalendarDateKey,
} from '@/components/ui/day-bucket-bar-chart'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import { MOCK_ISSUE_ROWS, type MockIssueRow } from '@/lib/mock-agent-dashboard'
import { useGetAgentStatsQuery } from '@/store/agents'
import { useGetActiveRunQuery, useGetRunEventsQuery } from '@/store/runs'
import type { AgentRun } from '@/types'

// ─── helpers ────────────────────────────────────────────────────────────────

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

function formatUsd(v: number): string {
  if (v === 0) return '$0'
  if (v < 0.01) return `$${v.toFixed(4)}`
  if (v < 1) return `$${v.toFixed(3)}`
  return `$${v.toFixed(2)}`
}

const RUN_STATUS: Record<string, { label: string; className: string }> = {
  completed: { label: 'DONE',    className: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' },
  running:   { label: 'RUN',     className: 'border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-400' },
  queued:    { label: 'QUEUED',  className: 'border-border text-muted-foreground' },
  failed:    { label: 'FAIL',    className: 'border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-400' },
  cancelled: { label: 'CANCEL',  className: 'border-border text-muted-foreground' },
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

function RunRow({ run, onViewDetails }: { run: AgentRun; onViewDetails?: () => void }) {
  const cfg = RUN_STATUS[run.status] ?? { label: run.status.toUpperCase(), className: 'border-border text-muted-foreground' }
  const duration = formatDuration(run.durationSeconds)
  const label = run.item ? `#${run.item.number} ${run.item.title}` : run.error ?? run.runId.slice(0, 8)

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
      {run.durationSeconds > 0 && (
        <span className="inline-flex shrink-0 items-center gap-0.5 border border-border px-1 py-px font-mono text-[9px] tracking-widest text-muted-foreground">
          <Clock className="size-2.5" />
          {duration}
        </span>
      )}
      <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-muted-foreground">
        {label}
      </span>
      <span className="shrink-0 font-mono text-[10px] text-muted-foreground/60">
        {formatRelativeTime(run.startedAt)}
      </span>
    </div>
  )
}

// ─── daily aggregation helpers ──────────────────────────────────────────────

function groupByDay(runs: AgentRun[], days = 7): DayGroup<AgentRun>[] {
  return buildDayGroupsForLastNDays(runs, (r) => timestampToLocalCalendarDateKey(r.startedAt), { days })
}

function toBuckets<T>(groups: DayGroup<T>[], reducer: (items: T[]) => number): DayBucket[] {
  return groups.map((g) => ({ label: g.label, dateKey: g.dateKey, value: reducer(g.items) }))
}

const CHART_CONFIG_RUNS: ChartConfig = {
  value: { label: 'Runs', color: 'oklch(0.78 0.14 158 / 0.78)' },
}
const CHART_CONFIG_FAILURES: ChartConfig = {
  value: { label: 'Failed', color: 'oklch(0.58 0.2 27 / 0.88)' },
}
const CHART_CONFIG_COST: ChartConfig = {
  value: { label: 'Cost', color: 'oklch(0.72 0.16 75 / 0.88)' },
}
const CHART_CONFIG_ISSUES: ChartConfig = {
  value: { label: 'Issues', color: 'oklch(0.62 0.14 240 / 0.88)' },
}

// ─── main component ──────────────────────────────────────────────────────────

export function AgentDashboardTab({
  workspaceId,
  agentSlug,
  onViewRunDetails,
}: {
  workspaceId: string
  agentSlug: string
  onViewRunDetails?: () => void
}) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  const { data: stats, isLoading } = useGetAgentStatsQuery(
    { workspaceId, agentSlug },
    { skip: !workspaceId || !agentSlug },
  )

  const { data: activeRun } = useGetActiveRunQuery(
    { workspaceId },
    { skip: !workspaceId, pollingInterval: 3000 },
  )

  const { data: activeRunEvents } = useGetRunEventsQuery(
    { workspaceId, runId: activeRun?.run_id ?? '' },
    { skip: !activeRun?.run_id, pollingInterval: 2000 },
  )

  const runs = stats?.runs ?? []
  const dayGroups = groupByDay(runs, 10)
  const runActivity = toBuckets(dayGroups, (rs) => rs.length)
  const runFailures = toBuckets(dayGroups, (rs) => rs.filter((r) => r.status === 'failed').length)
  const runCost = toBuckets(dayGroups, (rs) => rs.reduce((sum, r) => sum + (r.tokenUsage?.cost_usd ?? 0), 0))
  const issueDayGroups = buildDayGroupsForLastNDays(
    MOCK_ISSUE_ROWS,
    (row) => timestampToLocalCalendarDateKey(row.createdAt),
  )
  const issueActivity = toBuckets(issueDayGroups, (rows) => rows.length)

  const openSheet = (runId: string) => {
    setSelectedRunId(runId)
    setSheetOpen(true)
  }

  const renderNow = () => {
    if (!activeRun) return null
    const claimEvent = activeRunEvents?.find(
      (e) => e.type === 'agent.claimed_issue' || e.type === 'agent.claimed_pr',
    )
    const label = claimEvent
      ? `#${(claimEvent.data as { number: number }).number}  ${(claimEvent.data as { title: string }).title}`
      : activeRun.run_id.slice(0, 8)
    return (
      <section className="border border-blue-500/30 bg-blue-500/5">
        <SectionBar title="Now · 1 active task" />
        <button
          type="button"
          onClick={() => openSheet(activeRun.run_id)}
          className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-blue-500/10"
        >
          <Loader2 className="size-3 shrink-0 animate-spin text-blue-400" />
          <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-blue-300">{label}</span>
          <span className="shrink-0 font-mono text-[10px] text-muted-foreground/60">active</span>
        </button>
      </section>
    )
  }

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
      {isLoading ? (
        <div className="flex items-center gap-2 px-3 py-3">
          <Loader2 className="size-3 animate-spin text-muted-foreground" />
          <span className="font-mono text-[10px] tracking-widest text-muted-foreground">LOADING...</span>
        </div>
      ) : runs.length === 0 ? (
        <p className="px-3 py-3 font-mono text-[11px] text-muted-foreground">No runs yet.</p>
      ) : (
        <ul className="divide-y divide-border/60">
          {[...runs].sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()).slice(0, 5).map((run) => (
            <li key={run.runId}>
              <RunRow run={run} onViewDetails={() => openSheet(run.runId)} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )

  const renderSheet = () => (
    <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
      <SheetContent side="right" className="flex !w-[80vw] !max-w-[80vw] flex-col rounded-none p-0 sm:!max-w-[80vw] gap-0">
        <SheetHeader className="shrink-0 border-b border-border/60 p-4">
          <SheetTitle className="font-mono text-[11px] font-normal text-muted-foreground">
            Run:  <b>{selectedRunId}</b>
          </SheetTitle>
        </SheetHeader>
        {selectedRunId && (
          <RunLogView
            workspaceId={workspaceId}
            runId={selectedRunId}
            isActive={activeRun?.run_id === selectedRunId}
            agentFilter={agentSlug}
          />
        )}
      </SheetContent>
    </Sheet>
  )

  const renderCharts = () => (
    <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
      <AgentDashboardBarChartCard
        title="Total runs"
        subtitle="Last 10 days"
        buckets={runActivity}
        config={CHART_CONFIG_RUNS}
        emptyLabel="No runs"
      />
      <AgentDashboardBarChartCard
        title="Failed runs"
        subtitle="Last 10 days"
        buckets={runFailures}
        config={CHART_CONFIG_FAILURES}
        emptyLabel="No failures"
      />
      <AgentDashboardBarChartCard
        title="Run cost"
        subtitle="Last 10 days"
        buckets={runCost}
        config={CHART_CONFIG_COST}
        emptyLabel="No cost"
        formatTooltipValue={formatUsd}
      />
      <AgentDashboardBarChartCard
        title="Issues created"
        subtitle="Last 7 days"
        buckets={issueActivity}
        config={CHART_CONFIG_ISSUES}
        emptyLabel="No issues"
      />
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
        {[...MOCK_ISSUE_ROWS]
          .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
          .map((row) => (
            <li key={row.id} className="flex items-start gap-3 px-3 py-2">
              <span className="shrink-0 font-mono text-[10px] text-muted-foreground">{row.id}</span>
              <span className="min-w-0 flex-1 text-[12px] leading-snug">{row.title}</span>
              <IssueStatusBadge row={row} />
            </li>
          ))}
      </ul>
    </section>
  )

  return (
    <>
      <div className="flex flex-col gap-4 p-4">
        {renderNow()}
        {renderRuns()}
        {renderCharts()}
        {renderIssues()}
      </div>
      {renderSheet()}
    </>
  )
}
