import { useNavigate } from 'react-router'
import { ListTodo, MessageCircle, Pause, Play } from 'lucide-react'
import { AgentIcon } from '@/components/agents/agent-icon'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import type { Agent } from '@/types'

type StatusKey = 'active' | 'archived' | 'error' | 'paused'

const STATUS_CONFIG: Record<
  StatusKey,
  { label: string; edge: string; text: string; dot: string }
> = {
  active: {
    label: 'LIVE',
    edge: 'bg-emerald-500',
    text: 'text-emerald-600 dark:text-emerald-400',
    dot: 'bg-emerald-500 animate-pulse',
  },
  archived: {
    label: 'OFF',
    edge: 'bg-muted-foreground/30',
    text: 'text-muted-foreground',
    dot: 'bg-muted-foreground/50',
  },
  error: {
    label: 'ERR',
    edge: 'bg-red-500',
    text: 'text-red-600 dark:text-red-400',
    dot: 'bg-red-500',
  },
  paused: {
    label: 'HOLD',
    edge: 'bg-amber-500',
    text: 'text-amber-600 dark:text-amber-400',
    dot: 'bg-amber-500',
  },
}

function getStatus(s: string) {
  return STATUS_CONFIG[s as StatusKey] ?? STATUS_CONFIG.active
}

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function AgentCard({
  agent,
  to,
}: {
  agent: Agent
  to: string
}) {
  const navigate = useNavigate()
  const status = getStatus(agent.status)
  const isPaused = agent.status === 'paused'

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
      className={cn(
        'group relative flex cursor-pointer border border-border bg-card outline-none rounded-md overflow-hidden',
        'transition-colors hover:bg-accent/50',
        'focus-visible:ring-2 focus-visible:ring-ring',
      )}
    >
      {/* Status edge */}
      <div className={cn('w-[3px] shrink-0', status.edge)} />

      {/* Content */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top row — icon, identity, status */}
        <div className="flex items-center gap-2.5 px-3 py-2">
          <AgentIcon slug={agent.slug} className="size-6" />

          <div className="flex min-w-0 flex-1 items-center gap-2">
            <span className="truncate text-[13px] font-semibold leading-none">
              {agent.name}
            </span>
            <span className="font-mono text-[10px] leading-none text-muted-foreground/60">
              /{agent.slug}
            </span>
          </div>

          <div className={cn('flex items-center gap-1', status.text)}>
            <span className={cn('size-1.5 rounded-full', status.dot)} />
            <span className="font-mono text-[9px] font-bold tracking-widest">
              {status.label}
            </span>
          </div>
        </div>

        {/* Description */}
        <div className="border-t border-dashed border-border/60 px-3 py-1.5">
          <p className="text-[11px] leading-snug text-muted-foreground">
            {agent.adapterType}
            {agent.skills.length > 0 && ` · ${agent.skills.length} skill${agent.skills.length > 1 ? 's' : ''}`}
          </p>
        </div>

        {/* Meta strip */}
        <div className="flex items-center gap-3 border-t border-dashed border-border/60 px-3 py-1.5 font-mono text-[10px] text-muted-foreground/70">
          <span>{agent.adapterType}</span>
          <span className="text-border">|</span>
          <span>Created {formatRelativeTime(agent.createdAt)}</span>
        </div>

        {/* Action toolbar */}
        <div className="flex items-center border-t border-border bg-muted/30">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="xs"
                  className="h-7 flex-1 rounded-none text-[11px] font-normal text-muted-foreground hover:text-foreground"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ListTodo className="size-3" />
                  Task
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                Assign a task to {agent.name}
              </TooltipContent>
            </Tooltip>

            <div className="h-3.5 w-px bg-border" />

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="xs"
                  className="h-7 flex-1 rounded-none text-[11px] font-normal text-muted-foreground hover:text-foreground"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MessageCircle className="size-3" />
                  Chat
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                Chat with {agent.name}
              </TooltipContent>
            </Tooltip>

            <div className="h-3.5 w-px bg-border" />

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="xs"
                  className={cn(
                    'h-7 flex-1 rounded-none text-[11px] font-normal',
                    !isPaused &&
                      'text-amber-600/70 hover:bg-amber-500/10 hover:text-amber-700 dark:text-amber-400/70 dark:hover:text-amber-300',
                    isPaused &&
                      'text-emerald-600/70 hover:bg-emerald-500/10 hover:text-emerald-700 dark:text-emerald-400/70 dark:hover:text-emerald-300',
                  )}
                  onClick={(e) => e.stopPropagation()}
                >
                  {isPaused ? (
                    <Play className="size-3" />
                  ) : (
                    <Pause className="size-3" />
                  )}
                  {isPaused ? 'Resume' : 'Pause'}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                {isPaused ? `Resume ${agent.name}` : `Pause ${agent.name}`}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>
    </div>
  )
}
