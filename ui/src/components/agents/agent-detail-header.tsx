import { Link } from 'react-router'
import { Loader2, MoreHorizontal, Pause, Play, Plus } from 'lucide-react'
import { AgentIcon } from '@/components/agents/agent-icon'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { Agent } from '@/types'

export function AgentDetailHeader({
  agent,
  basePath,
  onAssignTask,
  onRunHeartbeat,
  onTogglePause,
  assignLoading,
  heartbeatLoading,
  pauseLoading,
}: {
  agent: Agent
  basePath: string
  onAssignTask: () => void
  onRunHeartbeat: () => void
  onTogglePause: () => void
  assignLoading: boolean
  heartbeatLoading: boolean
  pauseLoading: boolean
}) {
  const isPaused = agent.status === 'paused'
  const busy = assignLoading || heartbeatLoading || pauseLoading

  const copyId = () => {
    void navigator.clipboard.writeText(agent.id)
  }

  return (
    <div className="flex flex-col gap-3 border-b border-dashed border-border/60 px-4 py-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex min-w-0 gap-3">
        <AgentIcon slug={agent.slug} className="size-10" iconClassName="size-4" />
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold tracking-tight">{agent.name}</h1>
          <p className="text-[13px] text-muted-foreground">
            {agent.adapterType}
            <span className="font-mono text-muted-foreground/70"> · /{agent.slug}</span>
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 sm:justify-end">
        <Button
          variant="default"
          size="xs"
          className="rounded-none"
          disabled={busy}
          onClick={onAssignTask}
        >
          {assignLoading ? (
            <Loader2 className="size-3 animate-spin" />
          ) : (
            <Plus className="size-3" />
          )}
          Assign task
        </Button>
        <Button
          variant="secondary"
          size="xs"
          className="rounded-none"
          disabled={busy}
          onClick={onRunHeartbeat}
        >
          {heartbeatLoading ? (
            <Loader2 className="size-3 animate-spin" />
          ) : (
            <Play className="size-3" />
          )}
          Run heartbeat
        </Button>
        <Button
          variant="outline"
          size="xs"
          className="rounded-none"
          disabled={busy}
          onClick={onTogglePause}
        >
          {pauseLoading ? (
            <Loader2 className="size-3 animate-spin" />
          ) : isPaused ? (
            <Play className="size-3" />
          ) : (
            <Pause className="size-3" />
          )}
          {isPaused ? 'Resume' : 'Pause'}
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-xs" className="rounded-none" disabled={busy}>
              <MoreHorizontal className="size-4" />
              <span className="sr-only">More actions</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={copyId}>Copy agent id</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to={`${basePath}/agents`}>Back to all agents</Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
