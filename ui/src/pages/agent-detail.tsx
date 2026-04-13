import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { toast } from 'sonner'
import {
  AgentDashboardTab,
  AgentDetailHeader,
  AssignTaskDialog,
} from '@/components/agents'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useGetAgentQuery, useUpdateAgentMutation } from '@/store/agents'
import { useCreateRunMutation } from '@/store/runs'
import type { Agent } from '@/types'

function PlaceholderTab({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="p-4">
      <p className="text-[13px] font-medium">{title}</p>
      <div className="mt-3 text-[12px] text-muted-foreground">{children}</div>
    </div>
  )
}

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="mt-2 max-h-[min(50vh,420px)] overflow-auto border border-border bg-muted/20 p-3 font-mono text-[11px] leading-relaxed">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}

function SkillsTab({ agent }: { agent: Agent }) {
  return (
    <PlaceholderTab title="Skills">
      {agent.skills.length === 0 ? (
        <span>No skills configured.</span>
      ) : (
        <ul className="mt-2 list-inside list-disc space-y-1 text-foreground">
          {agent.skills.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      )}
    </PlaceholderTab>
  )
}

function ConfigurationTab({ agent }: { agent: Agent }) {
  return (
    <PlaceholderTab title="Adapter configuration">
      <JsonBlock value={agent.adapterConfig} />
    </PlaceholderTab>
  )
}

export default function AgentDetail() {
  const { orgSlug, agentSlug } = useParams<{ orgSlug: string; agentSlug: string }>()
  const base = orgSlug ? `/${orgSlug}` : ''
  const [tab, setTab] = useState('dashboard')
  const [assignOpen, setAssignOpen] = useState(false)

  const skip = !orgSlug || !agentSlug
  const {
    data: agent,
    isLoading,
    isError,
    error,
    refetch,
  } = useGetAgentQuery(
    { orgSlug: orgSlug!, agentSlug: agentSlug! },
    { skip },
  )

  const [createRun, { isLoading: createRunLoading }] = useCreateRunMutation()
  const [updateAgent, { isLoading: updateAgentLoading }] = useUpdateAgentMutation()
  const [runAction, setRunAction] = useState<'assign' | 'heartbeat' | null>(null)

  const pauseLoading = updateAgentLoading
  const assignBtnLoading = createRunLoading && runAction === 'assign'
  const heartbeatLoading = createRunLoading && runAction === 'heartbeat'

  const handleAssignSubmit = async (message: string) => {
    if (!orgSlug || !agent) return
    setRunAction('assign')
    try {
      await createRun({
        orgSlug,
        body: { agent: agent.slug, message },
      }).unwrap()
      toast.success('Run queued')
      setAssignOpen(false)
    } catch {
      toast.error('Could not start run')
    } finally {
      setRunAction(null)
    }
  }

  const handleHeartbeat = async () => {
    if (!orgSlug || !agent) return
    setRunAction('heartbeat')
    try {
      await createRun({
        orgSlug,
        body: { agent: agent.slug, message: null },
      }).unwrap()
      toast.success('Heartbeat run queued')
    } catch {
      toast.error('Could not start heartbeat run')
    } finally {
      setRunAction(null)
    }
  }

  const handleTogglePause = async () => {
    if (!orgSlug || !agent) return
    const next = agent.status === 'paused' ? 'active' : 'paused'
    try {
      await updateAgent({
        orgSlug,
        agentIdOrSlug: agent.slug,
        body: { status: next },
      }).unwrap()
      toast.success(next === 'paused' ? 'Agent paused' : 'Agent resumed')
    } catch {
      toast.error('Could not update agent')
    }
  }

  const renderError = () => (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8">
      <p className="text-[13px] text-muted-foreground">
        {error && 'status' in error && error.status === 404
          ? 'Agent not found.'
          : 'Could not load this agent.'}
      </p>
      <Button variant="outline" size="xs" className="rounded-none" asChild>
        <Link to={`${base}/agents`}>Back to agents</Link>
      </Button>
      <Button variant="ghost" size="xs" className="rounded-none" onClick={() => refetch()}>
        Retry
      </Button>
    </div>
  )

  const renderLoading = () => (
    <div className="flex flex-1 items-center justify-center p-12">
      <div className="font-mono text-[12px] text-muted-foreground">Loading agent…</div>
    </div>
  )

  const renderTabs = (a: Agent) => (
    <Tabs value={tab} onValueChange={setTab} className="flex min-h-0 flex-1 flex-col">
      <TabsList className="h-auto w-full justify-start overflow-x-auto rounded-none border-b border-border bg-muted/10 px-2">
        <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
        <TabsTrigger value="instructions">Instructions</TabsTrigger>
        <TabsTrigger value="skills">Skills</TabsTrigger>
        <TabsTrigger value="configuration">Configuration</TabsTrigger>
        <TabsTrigger value="runs">Runs</TabsTrigger>
        <TabsTrigger value="budget">Budget</TabsTrigger>
      </TabsList>
      <TabsContent value="dashboard" className="mt-0 min-h-0 flex-1">
        <AgentDashboardTab onViewRunDetails={() => setTab('runs')} />
      </TabsContent>
      <TabsContent value="instructions" className="mt-0 min-h-0 flex-1">
        <PlaceholderTab title="Instructions">
          Agent instructions will appear here when loaded from the agent workspace files.
        </PlaceholderTab>
      </TabsContent>
      <TabsContent value="skills" className="mt-0 min-h-0 flex-1">
        <SkillsTab agent={a} />
      </TabsContent>
      <TabsContent value="configuration" className="mt-0 min-h-0 flex-1">
        <ConfigurationTab agent={a} />
      </TabsContent>
      <TabsContent value="runs" className="mt-0 min-h-0 flex-1">
        <PlaceholderTab title="Runs">
          Run history will appear here when connected to the runs API in this view.
        </PlaceholderTab>
      </TabsContent>
      <TabsContent value="budget" className="mt-0 min-h-0 flex-1">
        <PlaceholderTab title="Budget">
          Budget and limits will appear here when available.
        </PlaceholderTab>
      </TabsContent>
    </Tabs>
  )

  const renderMain = () => {
    if (skip) return renderError()
    if (isLoading) return renderLoading()
    if (isError || !agent) return renderError()

    return (
      <>
        <AgentDetailHeader
          agent={agent}
          basePath={base}
          onAssignTask={() => setAssignOpen(true)}
          onRunHeartbeat={handleHeartbeat}
          onTogglePause={handleTogglePause}
          assignLoading={assignBtnLoading}
          heartbeatLoading={heartbeatLoading}
          pauseLoading={pauseLoading}
        />
        {renderTabs(agent)}
        <AssignTaskDialog
          open={assignOpen}
          onOpenChange={setAssignOpen}
          onSubmit={handleAssignSubmit}
          isSubmitting={assignBtnLoading}
          agentName={agent.name}
        />
      </>
    )
  }

  return <div className="flex min-h-0 flex-1 flex-col">{renderMain()}</div>
}
