import { useEffect, useRef } from 'react'
import { createChart, ColorType, LineStyle } from 'lightweight-charts'
import { useStore } from '../store/useStore'

export function PriceChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const candleRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const bbUpperRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const bbMidRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const bbLowerRef = useRef<any>(null)
  const { dailyPrices, price, indicators } = useStore()

  useEffect(() => {
    if (!containerRef.current) return
    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0a1628' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#0d1a2e' },
        horzLines: { color: '#0d1a2e' },
      },
      timeScale: { borderColor: '#1a3a5c' },
      rightPriceScale: { borderColor: '#1a3a5c' },
      width: containerRef.current.clientWidth || 600,
      height: 380,
    })
    chartRef.current = chart
    candleRef.current = chart.addCandlestickSeries()
    bbUpperRef.current = chart.addLineSeries({
      color: '#f0a500', lineWidth: 1, lineStyle: LineStyle.Dashed,
    })
    bbMidRef.current = chart.addLineSeries({ color: '#555', lineWidth: 1 })
    bbLowerRef.current = chart.addLineSeries({
      color: '#f0a500', lineWidth: 1, lineStyle: LineStyle.Dashed,
    })

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    })
    if (containerRef.current.parentElement) {
      ro.observe(containerRef.current.parentElement)
    }

    return () => { chart.remove(); ro.disconnect() }
  }, [])

  useEffect(() => {
    if (!candleRef.current || !dailyPrices.length) return
    const data = dailyPrices.map(d => ({
      time: d.date as `${number}-${number}-${number}`,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }))
    candleRef.current.setData(data)
  }, [dailyPrices])

  useEffect(() => {
    if (!indicators || !dailyPrices.length) return
    const lastDate = dailyPrices[dailyPrices.length - 1].date as `${number}-${number}-${number}`
    bbUpperRef.current?.update({ time: lastDate, value: indicators.bb_upper })
    bbMidRef.current?.update({ time: lastDate, value: indicators.bb_mid })
    bbLowerRef.current?.update({ time: lastDate, value: indicators.bb_lower })
  }, [indicators, price, dailyPrices])

  return <div ref={containerRef} style={{ width: '100%' }} />
}
