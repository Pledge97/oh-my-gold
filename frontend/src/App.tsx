import { useEffect, useRef } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { useStore } from './store/useStore'
import { fetchSignals, fetchPerformance, fetchDailyPrices } from './api/client'
import { StatusBar } from './components/StatusBar'
import { PriceChart } from './components/PriceChart'
import { TickChart } from './components/TickChart'
import { SignalPanel } from './components/SignalPanel'
import { PerformanceStats } from './components/PerformanceStats'
import { PositionTable } from './components/PositionTable'

export default function App() {
  useWebSocket()
  const { setSignals, setPerformance, setDailyPrices, isMarketOpen, price } = useStore()
  // 记录已处理的最新信号 id，避免无新信号时重复刷新绩效统计。
  const latestSignalIdRef = useRef<number | null>(null)

  useEffect(() => {
    document.title = Number.isFinite(price) && price > 0
      ? `¥${price.toFixed(2)} | Gold Inspector`
      : 'Gold Inspector'
  }, [price])

  useEffect(() => {
    fetchSignals().then((signals) => {
      latestSignalIdRef.current = signals[0]?.id ?? null
      setSignals(signals)
    })
    fetchPerformance().then(setPerformance)
    fetchDailyPrices().then(setDailyPrices)
  }, [])

  useEffect(() => {
    if (!isMarketOpen) return
    const interval = setInterval(() => {
      fetchSignals().then((signals) => {
        const latestSignalId = signals[0]?.id ?? null
        setSignals(signals)
        if (latestSignalId !== latestSignalIdRef.current) {
          latestSignalIdRef.current = latestSignalId
          fetchPerformance().then(setPerformance)
        }
      })
    }, 30000)
    return () => clearInterval(interval)
  }, [isMarketOpen, setSignals, setPerformance])

  return (
    <div style={{ height: '100vh', background: '#060b14', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 扫描线 */}
      <div className="dashboard-scanline" />

      {/* 顶部状态栏 */}
      <StatusBar />

      {/* 主内容 */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* 中间区域：图表 + 右侧面板 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 600px', gap: 12, flex: 1, minHeight: 0, overflow: 'hidden' }}>
          {/* K线图 + Tick图 */}
          <div style={{
            overflow: 'hidden',
            display: 'flex',
            gap: 12,
            flexDirection: 'column',
            minHeight: 0,
          }}>
            <PriceChart />
            <TickChart />
          </div>

          {/* 右侧：信号面板上半，底仓下半 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0 }}>
            <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <SignalPanel />
            </div>
            <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <PositionTable />
            </div>
          </div>
        </div>

        {/* 底部绩效 */}
        <PerformanceStats />
      </div>
    </div>
  )
}
