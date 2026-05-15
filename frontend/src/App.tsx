import { useEffect } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { useStore } from './store/useStore'
import { fetchSignals, fetchPerformance, fetchDailyPrices } from './api/client'
import { StatusBar } from './components/StatusBar'
import { PriceChart } from './components/PriceChart'
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
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 12, flex: 1 }}>
          {/* K线图 */}
          <div style={{
            background: '#0a1628',
            border: '1px solid #1a3a5c',
            borderRadius: 4,
            overflow: 'hidden',
          }}>
            <div className="panel-title">
              AU积存金 · 日K
              <span style={{ marginLeft: 'auto', fontSize: 10, color: '#2a4a6a' }}>
                布林带 BB(20,2)
              </span>
            </div>
            <PriceChart />
          </div>

          {/* 右侧：信号 + 持仓 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <SignalPanel />
            <PositionTable />
          </div>
        </div>

        {/* 底部绩效 */}
        <PerformanceStats />
      </div>
    </div>
  )
}
