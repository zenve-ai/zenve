import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { WorkspaceRun } from '@/types'

function agentStatusDot(status: string) {
  if (status === 'completed') return 'bg-emerald-500'
  if (status === 'failed') return 'bg-red-500'
  if (status === 'running') return 'bg-blue-400'
  return 'bg-muted-foreground/30'
}

function agentStatusLabel(status: string) {
  if (status === 'completed') return 'DONE'
  if (status === 'failed') return 'FAILED'
  if (status === 'running') return 'RUNNING'
  if (status === 'skipped') return 'SKIPPED'
  return status.toUpperCase()
}

function agentStatusTextClass(status: string) {
  if (status === 'completed') return 'text-emerald-400'
  if (status === 'failed') return 'text-red-400'
  if (status === 'running') return 'text-blue-300'
  return 'text-muted-foreground/40'
}

interface ActiveRunPanelProps {
  run: WorkspaceRun
}

export function ActiveRunPanel({ run }: ActiveRunPanelProps) {
  const shortId = run.run_id.slice(0, 8).toUpperCase()
  const isRunning = run.status === 'running'

  return (
    <div className="border border-blue-500/25 bg-blue-500/5 mx-4 mt-4">
      {/* Header strip */}
      <div className="flex items-center gap-2.5 border-b border-blue-500/20 bg-blue-500/10 px-4 py-1.5">
        <Loader2 className="size-3 shrink-0 animate-spin text-blue-400" />
        <span className="font-mono text-[10px] font-bold tracking-widest text-blue-300">
          RUN {shortId} {isRunning ? 'IN PROGRESS' : 'QUEUED'}
        </span>
        <span className="ml-auto font-mono text-[10px] text-blue-400/50 tracking-widest">
          {run.agents.length} AGENT{run.agents.length !== 1 ? 'S' : ''}
        </span>
      </div>

      {/* Agent cards */}
      <div className="flex flex-wrap gap-px p-2">
        {run.agents.map((a) => (
          <div
            key={a.agent}
            className="flex items-center gap-2 border border-border/30 bg-background/60 px-3 py-2 min-w-32"
          >
            <span
              className={cn(
                'size-1.5 shrink-0 rounded-full',
                agentStatusDot(a.status),
                a.status === 'running' && 'animate-pulse',
              )}
            />
            <div className="flex flex-col gap-0.5">
              <span className="font-mono text-[11px] text-foreground/80">{a.agent}</span>
              <span className={cn('font-mono text-[10px] tracking-widest', agentStatusTextClass(a.status))}>
                {agentStatusLabel(a.status)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
