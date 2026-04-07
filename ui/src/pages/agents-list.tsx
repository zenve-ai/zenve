import { useParams } from 'react-router'
import { Bot, Loader2, Plus, Search } from 'lucide-react'
import { AgentCard } from '@/components/agents'
import { Button } from '@/components/ui/button'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { useListAgentsQuery } from '@/store/agents'

export default function AgentsList() {
  const { orgSlug } = useParams<{ orgSlug: string }>()
  const base = orgSlug ? `/${orgSlug}` : ''
  const { data: agents = [], isLoading } = useListAgentsQuery(
    { orgSlug: orgSlug! },
    { skip: !orgSlug },
  )

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      {/* Title bar — full width border */}
      <div className="flex items-center justify-between border-b border-dashed border-border/60 px-4 py-1 bg-muted/20">
        <div className="flex flex-start flex-col">
          <h1 className="text-lg font-semibold tracking-tight">Agents</h1>
        </div>

        <div className="flex items-center gap-1.5">
          <Button variant="ghost" size="icon-sm" className="rounded-none">
            <Search className="size-3.5" />
          </Button>
          <Button variant="outline" size="xs" className="rounded-none">
            <Plus className="size-3" />
            Create agent
          </Button>
        </div>
      </div>

      {/* Cards, loading, or empty */}
      <div className="flex min-h-0 flex-1 flex-col">
        {isLoading ? (
          <div className="flex flex-1 items-center justify-center">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        ) : agents.length === 0 ? (
          <Empty className="m-4 border border-dashed border-border/60 bg-muted/10">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Bot />
              </EmptyMedia>
              <EmptyTitle>No agents yet</EmptyTitle>
              <EmptyDescription>
                Create an agent to run automations and workflows for this
                organization.
              </EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
              <Button variant="outline" size="xs" className="rounded-none">
                <Plus data-icon="inline-start" />
                Create agent
              </Button>
            </EmptyContent>
          </Empty>
        ) : (
          <ul className="grid grid-cols-1 gap-2 p-4 md:grid-cols-2 2xl:grid-cols-3">
            {agents.map((agent) => (
              <li key={agent.id}>
                <AgentCard agent={agent} to={`${base}/agents/${agent.slug}`} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
