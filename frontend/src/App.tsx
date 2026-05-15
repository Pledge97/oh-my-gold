import { useEffect } from 'react'
import { Layout } from 'antd'
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
    <Layout style={{ minHeight: '100vh', background: '#0d0d0d' }}>
      <StatusBar />
      <Layout.Content style={{ padding: 16 }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 400px',
            gap: 16,
            marginBottom: 16,
          }}
        >
          <PriceChart />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <SignalPanel />
            <PositionTable />
          </div>
        </div>
        <PerformanceStats />
      </Layout.Content>
    </Layout>
  )
}
