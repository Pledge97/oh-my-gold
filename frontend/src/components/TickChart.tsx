import { useEffect, useRef } from 'react'
import { createChart, ColorType, LineStyle } from 'lightweight-charts'
import { useStore } from '../store/useStore'
import { fetchTickPrices } from '../api/client'

export function TickChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const lineRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const bbUpperRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const bbLowerRef = useRef<any>(null)
  const { price, indicators } = useStore()
  const lastTsRef = useRef<number>(0)

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
      timeScale: {
        timeVisible: true,
        secondsVisible: true,
        borderColor: '#1a3a5c',
      },
      rightPriceScale: { borderColor: '#1a3a5c' },
      crosshair: { vertLine: { color: '#00d4ff44' }, horzLine: { color: '#00d4ff44' } },
      width: containerRef.current.clientWidth,
      height: 200,
    })
    chartRef.current = chart

    lineRef.current = chart.addLineSeries({
      color: '#00d4ff',
      lineWidth: 1,
      priceLineVisible: true,
      lastValueVisible: true,
    })

    bbUpperRef.current = chart.addLineSeries({
      color: '#f0a50055',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    bbLowerRef.current = chart.addLineSeries({
      color: '#f0a50055',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // 加载历史 tick 数据
    fetchTickPrices(24).then((data: { ts: number; price: number }[]) => {
      if (!data.length) return
      const points = data.map(d => ({
        time: Math.floor(d.ts / 1000) as unknown as `${number}`,
        value: d.price,
      }))
      lineRef.current?.setData(points)
      lastTsRef.current = data[data.length - 1].ts
      chart.timeScale().fitContent()
    })

    return () => chart.remove()
  }, [])

  // 实时追加新 tick
  useEffect(() => {
    if (!price || !lineRef.current) return
    const nowSec = Math.floor(Date.now() / 1000)
    const nowMs = nowSec * 1000
    if (nowMs <= lastTsRef.current) return
    lastTsRef.current = nowMs
    lineRef.current.update({ time: nowSec as unknown as `${number}`, value: price })
  }, [price])

  // 实时更新布林带
  useEffect(() => {
    if (!indicators || !price) return
    const nowSec = Math.floor(Date.now() / 1000) as unknown as `${number}`
    bbUpperRef.current?.update({ time: nowSec, value: indicators.bb_upper })
    bbLowerRef.current?.update({ time: nowSec, value: indicators.bb_lower })
  }, [indicators, price])

  return (
    <div style={{ borderTop: '1px solid #1a3a5c' }}>
      <div style={{
        padding: '4px 12px',
        fontSize: 10,
        color: '#4fc3f7',
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        background: '#0d1a2e',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00d4ff', boxShadow: '0 0 6px #00d4ff', display: 'inline-block' }} />
        实时价格 · 过去24小时
        <span style={{ marginLeft: 'auto', color: '#f0a500', fontSize: 10 }}>
          BB({indicators?.bb_lower?.toFixed(2)} ~ {indicators?.bb_upper?.toFixed(2)})
        </span>
      </div>
      <div ref={containerRef} style={{ width: '100%' }} />
    </div>
  )
}
