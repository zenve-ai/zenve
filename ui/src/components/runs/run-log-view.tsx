import { useEffect, useMemo, useRef, useState } from 'react'
import { deriveAgentStates, groupEventsIntoBlocks, mergeRawEvents } from '@/lib/run-events'
import type { RunBlock } from '@/lib/run-events'
import { useGetRunEventsQuery } from '@/store/runs'
import { useRunStream } from '@/hooks/use-run-stream'
import { RunAgentStateBar } from './run-agent-state-bar'
import { RunLoadingIndicator } from './run-loading-indicator'
import { RunOutputBlock } from './run-output-block'
import { RunStatusLine } from './run-status-line'
import { RunToolBlock } from './run-tool-block'

interface RunLogViewProps {
  workspaceId: string
  runId: string
  isActive: boolean
  agentFilter?: string
}

export function RunLogView({ workspaceId, runId, isActive, agentFilter }: RunLogViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const isAtBottomRef = useRef(true)
  const [elapsed, setElapsed] = useState(0)
  const startedAtRef = useRef<number>(Date.now())

  const { data: historicalEvents = [] } = useGetRunEventsQuery(
    { workspaceId, runId },
    { skip: !workspaceId || !runId, refetchOnMountOrArgChange: true },
  )

  const liveEvents = useRunStream(workspaceId, runId, isActive)

  const mergedEvents = useMemo(
    () => mergeRawEvents(historicalEvents, liveEvents),
    [historicalEvents, liveEvents],
  )

  const filteredEvents = useMemo(
    () =>
      agentFilter
        ? mergedEvents.filter((e) => e.agent === null || e.agent === agentFilter)
        : mergedEvents,
    [mergedEvents, agentFilter],
  )

  const blocks = useMemo(() => groupEventsIntoBlocks(filteredEvents), [filteredEvents])
  const { agents, states, repo, runId: derivedRunId } = useMemo(
    () => deriveAgentStates(filteredEvents),
    [filteredEvents],
  )

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const onScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container
      isAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 40
    }
    container.addEventListener('scroll', onScroll, { passive: true })
    return () => container.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (isAtBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [blocks.length])

  useEffect(() => {
    if (!isActive) return
    startedAtRef.current = Date.now()
    setElapsed(0)
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAtRef.current) / 1000))
    }, 1000)
    return () => clearInterval(id)
  }, [isActive])

  const renderBlock = (block: RunBlock) => {
    if (block.kind === 'output') return <RunOutputBlock key={block.key} block={block} />
    if (block.kind === 'tool') return <RunToolBlock key={block.key} block={block} />
    return <RunStatusLine key={block.key} line={block} />
  }

  const renderContent = () => (
    <div ref={containerRef} className="flex-1 overflow-y-auto">
      <div className="divide-y divide-slate-200">
        {blocks.map(renderBlock)}
        {isActive && <RunLoadingIndicator elapsedSeconds={elapsed} />}
        {blocks.length === 0 && !isActive && (
          <p className="px-3 py-4 font-mono text-[11px] text-muted-foreground/50">No events yet.</p>
        )}
      </div>
      <div ref={bottomRef} />
    </div>
  )

  const renderMain = () => (
    <div className="flex h-full flex-col bg-slate-50">
      <RunAgentStateBar
        agents={agents}
        states={states}
        runId={derivedRunId ?? runId}
        repo={repo}
      />
      {renderContent()}
    </div>
  )

  return renderMain()
}
