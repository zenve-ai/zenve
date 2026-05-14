import { useEffect, useRef, useState } from 'react'
import config from '@/config'
import type { RawRunEvent } from '@/types'

export function useRunStream(
  workspaceId: string,
  runId: string | null,
  enabled: boolean,
): RawRunEvent[] {
  const [events, setEvents] = useState<RawRunEvent[]>([])
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!enabled || !workspaceId || !runId) {
      setEvents([])
      return
    }

    const controller = new AbortController()
    abortRef.current = controller
    setEvents([])

    const url = `${config.runtimeUrl}/workspaces/${workspaceId}/runs/${runId}/stream`

    async function stream() {
      try {
        const res = await fetch(url, { signal: controller.signal })
        if (!res.ok || !res.body) return
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          const lines = buf.split('\n')
          buf = lines.pop() ?? ''
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const event = JSON.parse(line.slice(6)) as RawRunEvent
              setEvents((prev) => [...prev, event])
            } catch {
              // ignore malformed lines
            }
          }
        }
      } catch {
        // aborted or network error — no-op
      }
    }

    stream()

    return () => {
      controller.abort()
      abortRef.current = null
    }
  }, [workspaceId, runId, enabled])

  return events
}
