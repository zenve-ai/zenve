import { cn, relativeTime } from '@/lib/utils'
import type { WorkspaceRun } from '@/types'

function statusBarClass(status: string) {
  if (status === 'completed') return 'bg-emerald-500'
  if (status === 'failed') return 'bg-red-500'
  if (status === 'running') return 'bg-blue-400'
  return 'bg-muted-foreground/30'
}

function statusTextClass(status: string) {
  if (status === 'completed') return 'text-emerald-400'
  if (status === 'failed') return 'text-red-400'
  if (status === 'running') return 'text-blue-400'
  return 'text-muted-foreground/40'
}

function agentIcon(status: string) {
  if (status === 'completed') return '●'
  if (status === 'failed') return '✗'
  if (status === 'running') return '◌'
  if (status === 'skipped') return '—'
  return '○'
}

function agentTextClass(status: string) {
  if (status === 'completed') return 'text-emerald-400'
  if (status === 'failed') return 'text-red-400'
  if (status === 'running') return 'text-blue-400'
  return 'text-muted-foreground/30'
}

function runDuration(started: string, finished: string): string {
  const s = Math.round((new Date(finished).getTime() - new Date(started).getTime()) / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}m ${rem}s`
}

interface RunRowProps {
  run: WorkspaceRun
}

export function RunRow({ run }: RunRowProps) {
  const shortId = run.run_id.slice(0, 8).toUpperCase()
  const ago = run.started_at ? relativeTime(run.started_at) : '—'
  const duration =
    run.started_at && run.finished_at ? runDuration(run.started_at, run.finished_at) : '—'

  return (
    <div className="relative flex items-center gap-0 border border-border/40 bg-background hover:bg-muted/10 transition-colors">
      <div className={cn('w-[3px] self-stretch shrink-0', statusBarClass(run.status))} />

      <div className="flex flex-1 items-center gap-4 px-4 py-2.5 min-w-0">
        {/* ID */}
        <span className="font-mono text-[11px] text-muted-foreground/60 w-20 shrink-0 tracking-widest">
          {shortId}
        </span>

        {/* Status */}
        <span className={cn('font-mono text-[10px] font-bold tracking-widest w-20 shrink-0', statusTextClass(run.status))}>
          {run.status.toUpperCase()}
        </span>

        {/* Time ago */}
        <span className="font-mono text-[10px] text-muted-foreground/40 w-16 shrink-0">
          {ago}
        </span>

        {/* Duration */}
        <span className="font-mono text-[10px] text-muted-foreground/30 w-16 shrink-0">
          {duration}
        </span>

        {/* Agent pills */}
        <div className="flex min-w-0 flex-wrap items-center gap-1">
          {run.agents.map((a) => (
            <span
              key={a.agent}
              className="flex items-center gap-1 border border-border/30 bg-muted/20 px-1.5 py-0.5"
            >
              <span className={cn('font-mono text-[10px]', agentTextClass(a.status))}>
                {agentIcon(a.status)}
              </span>
              <span className="font-mono text-[10px] text-muted-foreground/60">{a.agent}</span>
            </span>
          ))}
        </div>

        {/* Run-level error */}
        {run.status === 'failed' && run.error && (
          <span className="font-mono text-[10px] text-red-400/80 truncate max-w-xs" title={run.error}>
            {run.error}
          </span>
        )}
      </div>
    </div>
  )
}
