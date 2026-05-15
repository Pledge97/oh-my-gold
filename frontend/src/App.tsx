import { useEffect } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { useStore } from './store/useStore'
import { fetchSignals, fetchPerformance, fetchDailyPrices } from './api/client'
import { StatusBar } from './components/StatusBar'
import { PriceChart } from './components/PriceChart'
import { TickChart } from './components/TickChart'
import { SignalPanel } from './components/SignalPanel'
import { PositionTable } from './components/PositionTable'
import { PerformanceStats } from './components/PerformanceStats'

export default function App() {
  useWebSocket()
  const { setSignals, setPerformance, setDailyPrices } = useStore()

  useEffect(() => {
    fetchSignals().then(setSignals)
    fetchPerformance().then(setPerformance)
    fetchDailyPrices().then(setDailyPrices)
    const interval = setInterval(() => {
      fetchSignals().then(setSignals)
      fetchPerformance().then(setPerformance)
    }, 30000)
    return () => clearInterval(interval)
  }, [setSignals, setPerformance, setDailyPrices])

  return (
    <div style={{ minHeight: '100vh', background: '#060b14', display: 'flex', flexDirection: 'column' }}>
      {/* 扫描线 */}
      <div className="dashboard-scanline" />

      {/* 顶部状态栏 */}
      <StatusBar />

      {/* 主内容 */}
      <div style={{ flex: 1, padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* 中间区域：图表 + 右侧面板 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 480px', gap: 12, flex: 1 }}>
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

          {/* 右侧：信号 + 持仓，各占一半 */}
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
