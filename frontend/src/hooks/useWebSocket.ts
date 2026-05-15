import { useEffect, useRef } from 'react'
import { useStore } from '../store/useStore'

export function useWebSocket() {
  const setWsMessage = useStore(s => s.setWsMessage)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(`ws://${location.host}/ws`)
      wsRef.current = ws
      ws.onmessage = (e) => {
        try { setWsMessage(JSON.parse(e.data)) } catch {}
      }
      ws.onclose = () => setTimeout(connect, 3000)
      ws.onerror = () => ws.close()
    }
    connect()
    return () => wsRef.current?.close()
  }, [])
}
