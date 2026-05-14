import type { RawRunEvent } from '@/types'

export interface ToolCall {
  line: ToolCallLine
  key: string
}

export interface OutputBlock {
  kind: 'output'
  agent: string | null
  lines: string[]
  key: string
}

export interface ToolBlock {
  kind: 'tool'
  agent: string | null
  calls: ToolCall[]
  key: string
}

export interface StatusLine {
  kind: 'status'
  subtype: string
  agent: string | null
  data: Record<string, unknown>
  key: string
}

export type RunBlock = OutputBlock | ToolBlock | StatusLine

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function fmtArg(v: unknown, maxLen = 60): string {
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  const trimmed = s.length > maxLen ? s.slice(0, maxLen) + '…' : s
  return `"${trimmed}"`
}

export interface ToolCallLine {
  tool: string
  args: Array<{ key: string; value: string }>
}

export function parseToolCallLine(tool: string, input: Record<string, unknown> | null): ToolCallLine {
  if (!input) return { tool: capitalize(tool), args: [] }

  const order: string[] = []
  if (tool === 'read' || tool === 'Read') {
    order.push('file_path', 'filePath', 'path', 'offset', 'limit')
  } else if (tool === 'bash' || tool === 'Bash') {
    order.push('command')
  } else {
    order.push(...Object.keys(input))
  }

  const seen = new Set<string>()
  const args: Array<{ key: string; value: string }> = []
  for (const key of order) {
    if (seen.has(key) || !(key in input)) continue
    seen.add(key)
    args.push({ key, value: fmtArg(input[key]) })
  }
  // catch remaining keys not in order list
  for (const [key, val] of Object.entries(input)) {
    if (seen.has(key)) continue
    args.push({ key, value: fmtArg(val) })
    if (args.length >= 4) break
  }

  return { tool: capitalize(tool), args }
}

export function groupEventsIntoBlocks(events: RawRunEvent[]): RunBlock[] {
  const blocks: RunBlock[] = []
  let current: OutputBlock | ToolBlock | null = null
  let blockIndex = 0

  function flush() {
    if (current) {
      blocks.push(current)
      current = null
    }
  }

  for (const event of events) {
    if (event.type === 'adapter.output') {
      const msg = (event.data.message as string | undefined) ?? ''
      if (msg.startsWith('Session started:') || msg === '') continue

      const lines = msg.split('\n').filter((l) => l !== '')
      if (!lines.length) continue

      if (current?.kind === 'output' && current.agent === event.agent) {
        current.lines.push(...lines)
      } else {
        flush()
        current = {
          kind: 'output',
          agent: event.agent,
          lines,
          key: `out-${blockIndex++}-${event.timestamp}`,
        }
      }
    } else if (event.type === 'adapter.tool_result') {
      // silently skip — not displayed
    } else if (event.type === 'adapter.tool_call') {
      const tool = (event.data.tool as string) ?? 'unknown'
      const input = (event.data.input as Record<string, unknown> | null) ?? null
      const line = parseToolCallLine(tool, input)

      if (current?.kind === 'tool' && current.agent === event.agent) {
        current.calls.push({ line, key: `tc-${blockIndex++}-${event.timestamp}` })
      } else {
        flush()
        current = {
          kind: 'tool',
          agent: event.agent,
          calls: [{ line, key: `tc-${blockIndex++}-${event.timestamp}` }],
          key: `tool-${blockIndex++}-${event.timestamp}`,
        }
      }
    } else {
      flush()
      blocks.push({
        kind: 'status',
        subtype: event.type,
        agent: event.agent,
        data: event.data,
        key: `status-${blockIndex++}-${event.timestamp}`,
      })
    }
  }

  flush()
  return blocks
}

export function mergeRawEvents(historical: RawRunEvent[], live: RawRunEvent[]): RawRunEvent[] {
  if (!historical.length) return live
  const lastTs = historical[historical.length - 1].timestamp
  const newLive = live.filter((e) => e.timestamp > lastTs)
  return [...historical, ...newLive]
}

export type AgentState = 'pending' | 'running' | 'done' | 'failed'

export function deriveAgentStates(events: RawRunEvent[]): {
  agents: string[]
  states: Record<string, AgentState>
  repo: string | null
  runId: string | null
} {
  let agents: string[] = []
  const states: Record<string, AgentState> = {}
  let repo: string | null = null
  let runId: string | null = null

  for (const event of events) {
    if (!runId && event.run_id) runId = event.run_id

    if (event.type === 'run.started') {
      const list = (event.data.agents as string[] | undefined) ?? []
      agents = list
      repo = (event.data.repo as string | null) ?? null
      for (const a of list) states[a] = 'pending'
    } else if (event.type === 'agent.started' && event.agent) {
      states[event.agent] = 'running'
    } else if (
      (event.type === 'agent.completed' || event.type === 'agent.nothing_to_do') &&
      event.agent
    ) {
      states[event.agent] = 'done'
    } else if (event.type === 'agent.failed' && event.agent) {
      states[event.agent] = 'failed'
    }
  }

  return { agents, states, repo, runId }
}
