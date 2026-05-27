import { useEffect, useRef } from 'react'
import config from '@/config'
import { useAppDispatch } from '@/store/hooks'
import { runCreated, runStatusChanged, runEventReceived, runFinished, runsApi } from '@/store/runs'
import { wsConnecting, wsConnected, wsDisconnected, wsReconnecting, wsFailed } from '@/store/ws'
import type { Run, RunEvent } from '@/types'

const MAX_RETRIES = 5
const BASE_DELAY_MS = 1000

function buildWsUrl(workspaceId: string): string {
  const base = config.runtimeUrl
  if (base.startsWith('http')) {
    const wsBase = base.replace(/^https:\/\//, 'wss://').replace(/^http:\/\//, 'ws://')
    return `${wsBase}/workspaces/${workspaceId}/ws`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${base}/workspaces/${workspaceId}/ws`
}

export function useWorkspaceWebSocket(workspaceId: string): void {
  const dispatch = useAppDispatch()
  const retryCount = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!workspaceId) return

    let cancelled = false

    function connect() {
      dispatch(wsConnecting())
      const ws = new WebSocket(buildWsUrl(workspaceId))
      wsRef.current = ws

      ws.onopen = () => {
        retryCount.current = 0
        dispatch(wsConnected())
      }

      ws.onmessage = (event) => {
        let msg: { type: string; data: unknown }
        try {
          msg = JSON.parse(event.data)
        } catch {
          return
        }

        switch (msg.type) {
          case 'run.created':
            dispatch(runCreated(msg.data as Run))
            dispatch(runsApi.util.invalidateTags(['Run']))
            break
          case 'run.status_changed':
            dispatch(runStatusChanged(msg.data as { run_id: string; status: string; started_at: string | null }))
            break
          case 'run.event':
            dispatch(runEventReceived(msg.data as RunEvent))
            break
          case 'run.finished':
            dispatch(
              runFinished(
                msg.data as { run_id: string; status: string; outcome: string | null; finished_at: string },
              ),
            )
            dispatch(runsApi.util.invalidateTags(['Run']))
            break
        }
      }

      ws.onclose = () => {
        wsRef.current = null
        if (cancelled) return
        if (retryCount.current >= MAX_RETRIES) {
          dispatch(wsFailed())
          return
        }
        dispatch(wsReconnecting())
        const delay = BASE_DELAY_MS * 2 ** retryCount.current
        retryCount.current += 1
        timerRef.current = setTimeout(connect, delay)
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      cancelled = true
      if (timerRef.current) clearTimeout(timerRef.current)
      if (wsRef.current) wsRef.current.close()
      dispatch(wsDisconnected())
    }
  }, [workspaceId, dispatch])
}
