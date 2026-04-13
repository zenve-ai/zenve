import { ArrowRight, Check, Timer } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  MOCK_CHART_ISSUES_PRIORITY_DAYS,
  MOCK_CHART_ISSUES_STATUS,
  MOCK_CHART_RUN_ACTIVITY,
  MOCK_CHART_SUCCESS_RATE,
  MOCK_COST_ROWS,
  MOCK_COST_SUMMARY,
  MOCK_ISSUES_PRIORITY_LEGEND,
  MOCK_ISSUE_ROWS,
  MOCK_LATEST_RUN,
  type MockIssueRow,
} from '@/lib/mock-agent-dashboard'

function SectionBar({
  title,
  action,
}: {
  title: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between border-b border-dashed border-border/60 bg-muted/20 px-3 py-1.5">
      <span className="text-[13px] font-semibold tracking-tight">{title}</span>
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

function StackedPriorityChart() {
  return (
    <div className="flex h-24 items-end gap-px">
      {MOCK_CHART_ISSUES_PRIORITY_DAYS.map((day, col) => {
        const total = day.reduce((a, b) => a + b, 0) || 1
        return (
          <div key={col} className="flex min-w-0 flex-1 flex-col justify-end gap-px">
            {day.map((segment, row) => {
              const pct = (segment / total) * 100
              const legend = MOCK_ISSUES_PRIORITY_LEGEND[row]
              return (
                <div
                  key={legend.key}
                  className={cn('w-full min-h-[1px] rounded-[1px]', legend.className)}
                  style={{ height: `${pct}%` }}
                />
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

function IssueStatusBadge({ row }: { row: MockIssueRow }) {
  if (row.status === 'done') {
    return (
      <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] text-emerald-700 dark:text-emerald-400">
        done
      </span>
    )
  }
  if (row.status === 'in_progress') {
    return (
      <span className="rounded-full border border-blue-500/40 bg-blue-500/10 px-2 py-0.5 font-mono text-[10px] text-blue-700 dark:text-blue-400">
        active
      </span>
    )
  }
  return (
    <span className="rounded-full border border-border px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
      open
    </span>
  )
}

export function AgentDashboardTab({ onViewRunDetails }: { onViewRunDetails?: () => void }) {
  const latest = MOCK_LATEST_RUN

  const renderLatestRun = () => (
    <section className="border border-border bg-card">
      <SectionBar
        title="Latest run"
        action={
          <Button
            variant="ghost"
            size="xs"
            className="h-7 rounded-none text-[11px] font-normal text-muted-foreground hover:text-foreground"
            onClick={onViewRunDetails}
          >
            View details
            <ArrowRight className="size-3" />
          </Button>
        }
      />
      <div className="flex flex-wrap items-center gap-2 px-3 py-2.5">
        <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-emerald-700 dark:text-emerald-400">
          <Check className="size-3" />
          {latest.statusLabel}
        </span>
        <span className="font-mono text-[11px] text-muted-foreground">{latest.runIdShort}</span>
        <span className="inline-flex items-center gap-1 rounded-full border border-blue-500/35 bg-blue-500/10 px-2 py-0.5 font-mono text-[10px] text-blue-700 dark:text-blue-300">
          <Timer className="size-3" />
          {latest.triggerLabel}
        </span>
        <span className="ml-auto font-mono text-[11px] text-muted-foreground">{latest.relativeTime}</span>
      </div>
    </section>
  )

  const renderCharts = () => (
    <section className="border border-border bg-card">
      <SectionBar title="Analytics (mock)" />
      <div className="grid gap-3 p-3 md:grid-cols-2 2xl:grid-cols-4">
        <div className="flex min-w-0 flex-col border border-dashed border-border/60 bg-muted/10">
          <div className="border-b border-border/60 px-2 py-1.5">
            <p className="text-[12px] font-medium">Run activity</p>
            <p className="text-[10px] text-muted-foreground">Last 14 days</p>
          </div>
          <div className="p-2">
            <MiniBars values={MOCK_CHART_RUN_ACTIVITY} barClassName="bg-emerald-500/80" />
          </div>
        </div>
        <div className="flex min-w-0 flex-col border border-dashed border-border/60 bg-muted/10">
          <div className="border-b border-border/60 px-2 py-1.5">
            <p className="text-[12px] font-medium">Issues by priority</p>
            <p className="text-[10px] text-muted-foreground">Last 14 days</p>
          </div>
          <div className="p-2">
            <StackedPriorityChart />
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
              {MOCK_ISSUES_PRIORITY_LEGEND.map((L) => (
                <span key={L.key} className="inline-flex items-center gap-1.5 text-[10px] text-muted-foreground">
                  <span className={cn('size-2 rounded-[1px]', L.className)} />
                  {L.label}
                </span>
              ))}
            </div>
          </div>
        </div>
        <div className="flex min-w-0 flex-col border border-dashed border-border/60 bg-muted/10">
          <div className="border-b border-border/60 px-2 py-1.5">
            <p className="text-[12px] font-medium">Issues by status</p>
            <p className="text-[10px] text-muted-foreground">Last 14 days</p>
          </div>
          <div className="p-2">
            <MiniBars values={MOCK_CHART_ISSUES_STATUS} barClassName="bg-emerald-500/70" />
          </div>
        </div>
        <div className="flex min-w-0 flex-col border border-dashed border-border/60 bg-muted/10">
          <div className="border-b border-border/60 px-2 py-1.5">
            <p className="text-[12px] font-medium">Success rate</p>
            <p className="text-[10px] text-muted-foreground">Last 14 days</p>
          </div>
          <div className="p-2">
            <MiniBars values={MOCK_CHART_SUCCESS_RATE} barClassName="bg-emerald-500/85" />
          </div>
        </div>
      </div>
    </section>
  )

  const renderIssues = () => (
    <section className="border border-border bg-card">
      <SectionBar
        title="Recent issues"
        action={
          <Button
            variant="ghost"
            size="xs"
            className="h-7 rounded-none text-[11px] font-normal text-muted-foreground hover:text-foreground"
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
      {renderLatestRun()}
      {renderCharts()}
      {renderIssues()}
      {renderCosts()}
    </div>
  )
}
