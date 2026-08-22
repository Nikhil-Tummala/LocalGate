import { useEffect, useState } from 'react'
import type { Telemetry } from '../types'

const MAX_BACKOFF_MS = 5000

/** Subscribes to /ws/telemetry and reconnects with capped exponential backoff. */
export function useTelemetry() {
  const [data, setData] = useState<Telemetry | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let ws: WebSocket | null = null
    let timer: number | undefined
    let attempt = 0
    let stopped = false

    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${location.host}/ws/telemetry`)
      ws.onopen = () => {
        attempt = 0
        setConnected(true)
      }
      ws.onmessage = (e) => setData(JSON.parse(e.data) as Telemetry)
      ws.onclose = () => {
        setConnected(false)
        if (stopped) return
        timer = window.setTimeout(connect, Math.min(MAX_BACKOFF_MS, 500 * 2 ** attempt++))
      }
    }

    connect()
    return () => {
      stopped = true
      window.clearTimeout(timer)
      ws?.close()
    }
  }, [])

  return { data, connected }
}
