import { useEffect, useRef } from 'react'
import { useStore } from '../store/useStore'
import { fetchLatestPrice } from '../api/client'

export function useWebSocket() {
  const setWsMessage = useStore(s => s.setWsMessage)
  const setPrice = useStore(s => s.setPrice)
  const isMarketOpen = useStore(s => s.isMarketOpen)
  const wsRef = useRef<WebSocket | null>(null)
  const isMarketOpenRef = useRef(isMarketOpen)

  useEffect(() => {
    isMarketOpenRef.current = isMarketOpen
  }, [isMarketOpen])

  useEffect(() => {
    // 初始化时从数据库拉取最新价格，避免休市时显示 0
    fetchLatestPrice().then(({ price }) => { if (price) setPrice(price) })

    function connect() {
      const ws = new WebSocket(`ws://${location.host}/ws`)
      wsRef.current = ws
      ws.onmessage = (e) => {
        try { setWsMessage(JSON.parse(e.data)) } catch {}
      }
      ws.onclose = () => {
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
