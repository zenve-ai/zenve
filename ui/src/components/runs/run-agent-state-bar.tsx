import { cn } from '@/lib/utils'
import type { AgentState } from '@/lib/run-events'

const INDICATOR: Record<AgentState, { symbol: string; className: string }> = {
  running: { symbol: '●', className: 'text-sky-500 animate-pulse' },
  done:    { symbol: '✓', className: 'text-emerald-600' },
  failed:  { symbol: '✗', className: 'text-red-500' },
  pending: { symbol: '○', className: 'text-slate-400' },
}

interface RunAgentStateBarProps {
  agents: string[]
  states: Record<string, AgentState>
  runId: string | null
  repo?: string | null
}

export function RunAgentStateBar({ agents, states, runId, repo }: RunAgentStateBarProps) {
  return (
    <div className="flex items-center justify-between border-b border-slate-200 bg-white px-3 py-2 font-mono text-[11px]">
      <div className="flex items-center gap-3 text-slate-400">
        {runId && <span className="tracking-wider">{runId.slice(0, 8)}</span>}
        {repo && <span>{repo}</span>}
      </div>
      <div className="flex items-center gap-4">
        {agents.map((agent) => {
          const state = states[agent] ?? 'pending'
          const { symbol, className } = INDICATOR[state]
          return (
            <span key={agent} className={cn('flex items-center gap-1', className)}>
              <span>{symbol}</span>
              <span className="text-slate-500">{agent}</span>
            </span>
          )
        })}
      </div>
    </div>
  )
}
