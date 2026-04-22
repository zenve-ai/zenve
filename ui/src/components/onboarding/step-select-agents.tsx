import { cn } from '@/lib/utils'
import { MOCK_AGENTS } from './mock-agents'

interface StepSelectAgentsProps {
  selectedAgents: Set<string>
  onToggle: (id: string) => void
}

export function StepSelectAgents({ selectedAgents, onToggle }: StepSelectAgentsProps) {
  // --- render helpers ---
  const renderAgentCard = (agent: typeof MOCK_AGENTS[number]) => {
    const selected = selectedAgents.has(agent.id)
    return (
      <button
        key={agent.id}
        type="button"
        onClick={() => onToggle(agent.id)}
        className={cn(
          'flex items-stretch gap-0 border border-dashed text-left transition-colors',
          selected
            ? 'border-emerald-500/60 bg-emerald-500/5'
            : 'border-border/60 hover:border-border',
        )}
      >
        <div className={cn('w-[3px] shrink-0', selected ? 'bg-emerald-500' : 'bg-muted-foreground/20')} />
        <div className="flex flex-col gap-0.5 px-3 py-2.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-mono font-medium leading-tight">{agent.name}</span>
            <span className={cn(
              'text-[9px] font-mono tracking-widest uppercase',
              selected ? 'text-emerald-500' : 'text-muted-foreground/40',
            )}>
              {agent.category}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground leading-snug">{agent.description}</p>
        </div>
      </button>
    )
  }

  // --- return ---
  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="font-mono text-[10px] tracking-widest uppercase text-muted-foreground/50">
          Step 03 / 04
        </p>
        <h2 className="mt-1 text-lg font-semibold leading-tight">Select agents</h2>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Pick the agents to activate for this project. You can change this later.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {MOCK_AGENTS.map(renderAgentCard)}
      </div>

      {selectedAgents.size > 0 && (
        <p className="font-mono text-[10px] tracking-widest uppercase text-emerald-500">
          {selectedAgents.size} agent{selectedAgents.size !== 1 ? 's' : ''} selected
        </p>
      )}
    </div>
  )
}
