import { useEffect, useRef } from 'react'
import { getToken } from '@/lib/token'
import config from '@/config'
import { useAppDispatch } from '@/store/hooks'
import { runCreated, runStatusChanged, runEventReceived, runFinished } from '@/store/runs'
import { wsConnecting, wsConnected, wsDisconnected, wsReconnecting, wsFailed } from '@/store/ws'
import type { Run, RunEvent } from '@/types'

const MAX_RETRIES = 5
const BASE_DELAY_MS = 1000

function buildWsUrl(projectId: string, token: string): string {
  const base = config.apiUrl
    .replace(/^https:\/\//, 'wss://')
    .replace(/^http:\/\//, 'ws://')
  return `${base}/projects/${projectId}/ws?token=${encodeURIComponent(token)}`
}

export function useProjectWebSocket(projectId: string): void {
  const dispatch = useAppDispatch()
  const retryCount = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!projectId) return

    let cancelled = false

    function connect() {
      const token = getToken()
      if (!token) return

      dispatch(wsConnecting())
      const ws = new WebSocket(buildWsUrl(projectId, token))
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
  }, [projectId, dispatch])
}
