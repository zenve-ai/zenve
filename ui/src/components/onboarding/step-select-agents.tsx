import { cn } from '@/lib/utils'
import type { AgentTemplate } from '@/types'

interface StepSelectAgentsProps {
  templates: AgentTemplate[]
  isLoading: boolean
  selectedAgents: Set<string>
  onToggle: (id: string) => void
}

export function StepSelectAgents({ templates, isLoading, selectedAgents, onToggle }: StepSelectAgentsProps) {
  // --- render helpers ---
  const renderAgentCard = (template: AgentTemplate) => {
    const selected = selectedAgents.has(template.id)
    return (
      <button
        key={template.id}
        type="button"
        onClick={() => onToggle(template.id)}
        className={cn(
          'flex items-stretch gap-0 border border-dashed text-left transition-colors',
          selected
            ? 'border-emerald-500/60 bg-emerald-500/5'
            : 'border-border/60 hover:border-border',
        )}
      >
        <div className={cn('w-[3px] shrink-0', selected ? 'bg-emerald-500' : 'bg-muted-foreground/20')} />
        <div className="flex flex-col gap-0.5 px-3 py-2.5">
          <span className="text-[11px] font-mono font-medium leading-tight">{template.name}</span>
          <p className="text-[11px] text-muted-foreground leading-snug">{template.description}</p>
        </div>
      </button>
    )
  }

  const renderContent = () => {
    if (isLoading) {
      return (
        <p className="font-mono text-[10px] tracking-widest uppercase text-muted-foreground/40">
          Loading templates...
        </p>
      )
    }
    if (templates.length === 0) {
      return (
        <p className="font-mono text-[10px] tracking-widest uppercase text-muted-foreground/40">
          No templates available
        </p>
      )
    }
    return (
      <div className="grid grid-cols-2 gap-2">
        {templates.map(renderAgentCard)}
      </div>
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

      {renderContent()}

      {selectedAgents.size > 0 && (
        <p className="font-mono text-[10px] tracking-widest uppercase text-emerald-500">
          {selectedAgents.size} agent{selectedAgents.size !== 1 ? 's' : ''} selected
        </p>
      )}
    </div>
  )
}
