import { useNavigate } from 'react-router'
import { MoreHorizontal } from 'lucide-react'
import { AdapterIcon } from '@/components/agents/adapter-icon'
import { AgentIcon } from '@/components/agents/agent-icon'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { Agent } from '@/types'

type StatusKey = 'active' | 'archived' | 'error' | 'paused'

const STATUS_CONFIG: Record<StatusKey, { label: string; dot: string; text: string }> = {
  active:   { label: 'Online',   dot: 'bg-emerald-500',        text: 'text-emerald-600 dark:text-emerald-400' },
  paused:   { label: 'Unstable', dot: 'bg-amber-500',          text: 'text-amber-600 dark:text-amber-400' },
  error:    { label: 'Unstable', dot: 'bg-amber-500',          text: 'text-amber-600 dark:text-amber-400' },
  archived: { label: 'Offline',  dot: 'bg-muted-foreground/40', text: 'text-muted-foreground/70' },
}

function getStatus(s: string) {
  return STATUS_CONFIG[s as StatusKey] ?? STATUS_CONFIG.archived
}

export function AgentRow({ agent, to }: { agent: Agent; to: string }) {
  const navigate = useNavigate()
  const status = getStatus(agent.status)

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Open ${agent.name} agent`}
      onClick={() => navigate(to)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          navigate(to)
        }
      }}
      className="group flex items-center gap-3 border border-border/60 px-4 py-2.5 cursor-pointer outline-none transition-colors hover:bg-muted/20 focus-visible:bg-muted/30"
    >
      {/* Agent name + icon — flex-1 */}
      <div className="flex min-w-0 flex-1 items-center gap-2.5">
        <AgentIcon slug={agent.slug} className="size-6 shrink-0" />
        <div className="grid min-w-0">
          <span className="truncate text-[13px] font-semibold leading-none">{agent.name}</span>
          <span className="truncate font-mono text-[10px] text-muted-foreground/50 mt-0.5 leading-none">
            /{agent.slug}
          </span>
        </div>
      </div>

      {/* Status — w-24 */}
      <div className={cn('flex w-24 shrink-0 items-center gap-1.5', status.text)}>
        <span className={cn('size-1.5 rounded-full shrink-0', status.dot)} />
        <span className="text-[12px]">{status.label}</span>
      </div>

      {/* Adapter — w-32 */}
      <div className="flex w-32 shrink-0 items-center gap-1.5 text-muted-foreground">
        <AdapterIcon adapterType={agent.adapterType} className="size-3.5 shrink-0" />
        <span className="truncate text-[12px]">
          {agent.adapterType ? agent.adapterType.replace(/_/g, ' ') : '—'}
        </span>
      </div>

      {/* Model — w-44 */}
      <div className="w-44 shrink-0">
        <span className="truncate font-mono text-[11px] text-muted-foreground block">
          {agent.model || '—'}
        </span>
      </div>

      {/* Capabilities — w-28 */}
      <div className="flex w-28 shrink-0 items-center gap-1.5 text-[11px] text-muted-foreground/70">
        {agent.skills.length > 0 && (
          <span>{agent.skills.length} skill{agent.skills.length !== 1 ? 's' : ''}</span>
        )}
        {agent.skills.length > 0 && agent.tools.length > 0 && (
          <span className="text-border">·</span>
        )}
        {agent.tools.length > 0 && (
          <span>{agent.tools.length} tools</span>
        )}
        {agent.skills.length === 0 && agent.tools.length === 0 && '—'}
      </div>

      {/* Mode — w-20 */}
      <div className="w-20 shrink-0">
        <span className="text-[12px] text-muted-foreground">
          {agent.mode ? agent.mode.replace(/_/g, ' ') : '—'}
        </span>
      </div>

      {/* Actions */}
      <div onClick={(e) => e.stopPropagation()}>
        <Button
          variant="ghost"
          size="icon-sm"
          className="rounded-none opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground"
        >
          <MoreHorizontal className="size-3.5" />
        </Button>
      </div>
    </div>
  )
}
