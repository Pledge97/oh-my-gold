import { useEffect, useRef } from 'react'
import { useStore } from '../store/useStore'

export function useWebSocket() {
  const setWsMessage = useStore(s => s.setWsMessage)
  const isMarketOpen = useStore(s => s.isMarketOpen)
  const wsRef = useRef<WebSocket | null>(null)
  const isMarketOpenRef = useRef(isMarketOpen)

  // 保持 ref 与 state 同步，供 onclose 回调读取最新值
  useEffect(() => {
    isMarketOpenRef.current = isMarketOpen
  }, [isMarketOpen])

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(`ws://${location.host}/ws`)
      wsRef.current = ws
      ws.onmessage = (e) => {
        try { setWsMessage(JSON.parse(e.data)) } catch {}
      }
      ws.onclose = () => {
        // 休市时不重连，等市场开放后刷新页面即可
        if (isMarketOpenRef.current) {
          setTimeout(connect, 3000)
        }
      }
      ws.onerror = () => ws.close()
    }
    connect()
    return () => wsRef.current?.close()
  }, [])
}
