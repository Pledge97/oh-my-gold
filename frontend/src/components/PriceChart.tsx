import { useEffect, useRef } from 'react'
import { createChart, ColorType, LineStyle, type Time } from 'lightweight-charts'
import { useStore } from '../store/useStore'

// 图表横轴显示使用的本地化语言。
const CHART_LOCALE = 'zh-CN'
// 容器布局完成前，用于初始化横轴缩放计算的兜底宽度。
const DEFAULT_CHART_WIDTH = 600
// 容器高度尚未计算完成时的兜底高度。
const DEFAULT_CHART_HEIGHT = 380
// 第一根 K 线前保留的逻辑边距。
const LEFT_LOGICAL_PADDING = 0.5
// 最新一根 K 线后保留的逻辑边距。
const RIGHT_LOGICAL_PADDING = 1.5

/**
 * 按本地时区格式化图表横轴时间。
 *
 * @param time lightweight-charts 传入的时间值。
 * @returns 本地日期文本。
 */
function formatLocalChartTime(time: Time) {
  if (typeof time === 'string') {
    return new Date(`${time}T00:00:00`).toLocaleDateString(CHART_LOCALE)
  }
  if (typeof time === 'number') {
    return new Date(time * 1000).toLocaleDateString(CHART_LOCALE)
  }
  return new Date(time.year, time.month - 1, time.day).toLocaleDateString(CHART_LOCALE)
}

/**
 * 设置横轴可见逻辑范围，让日 K 默认占满图表宽度。
 *
 * @param chart lightweight-charts 图表实例。
 * @param dataLength K 线数据条数。
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function fillTimeScale(chart: any, dataLength: number) {
  if (!chart || dataLength <= 0) return
  chart.timeScale().setVisibleLogicalRange({
    from: -LEFT_LOGICAL_PADDING,
    to: dataLength - 1 + RIGHT_LOGICAL_PADDING
  })
}

export function PriceChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  const dataLengthRef = useRef(0)
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
        textColor: '#d1d4dc'
      },
      grid: {
        vertLines: { color: '#0d1a2e' },
        horzLines: { color: '#0d1a2e' }
      },
      localization: {
        locale: CHART_LOCALE,
        timeFormatter: formatLocalChartTime
      },
      timeScale: {
        borderColor: '#1a3a5c',
        tickMarkFormatter: formatLocalChartTime
      },
      rightPriceScale: { borderColor: '#1a3a5c' },
      width: containerRef.current.clientWidth || DEFAULT_CHART_WIDTH,
      height: containerRef.current.clientHeight || DEFAULT_CHART_HEIGHT
    })
    chartRef.current = chart
    candleRef.current = chart.addCandlestickSeries()
    bbUpperRef.current = chart.addLineSeries({
      color: '#f0a500',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed
    })
    bbMidRef.current = chart.addLineSeries({ color: '#555', lineWidth: 1 })
    bbLowerRef.current = chart.addLineSeries({
      color: '#f0a500',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed
    })

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        const width = containerRef.current.clientWidth || DEFAULT_CHART_WIDTH
        const height = containerRef.current.clientHeight || DEFAULT_CHART_HEIGHT
        chart.applyOptions({ width, height })
        fillTimeScale(chart, dataLengthRef.current)
      }
    })
    ro.observe(containerRef.current)

    return () => {
      chart.remove()
      ro.disconnect()
    }
  }, [])

  useEffect(() => {
    if (!candleRef.current || !dailyPrices.length) return
    const data = dailyPrices.map((d) => ({
      time: d.date as `${number}-${number}-${number}`,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close
    }))
    dataLengthRef.current = data.length
    candleRef.current.setData(data)
    fillTimeScale(chartRef.current, data.length)
  }, [dailyPrices])

  useEffect(() => {
    if (!indicators || !dailyPrices.length) return
    const lastDate = dailyPrices[dailyPrices.length - 1].date as `${number}-${number}-${number}`
    bbUpperRef.current?.update({ time: lastDate, value: indicators.bb_upper })
    bbMidRef.current?.update({ time: lastDate, value: indicators.bb_mid })
    bbLowerRef.current?.update({ time: lastDate, value: indicators.bb_lower })
  }, [indicators, price, dailyPrices])

  return (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', border: '1px solid #1a3a5c', borderRadius: 4 }}>
      <div
        style={{
          padding: '4px 12px',
          fontSize: 10,
          color: '#4fc3f7',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          background: '#0d1a2e',
          display: 'flex',
          alignItems: 'center',
          gap: 8
        }}
      >
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00d4ff', boxShadow: '0 0 6px #00d4ff', display: 'inline-block' }} />
        AU积存金 · 日K
        <span style={{ marginLeft: 'auto', color: '#2a4a6a', fontSize: 10 }}>布林带 BB(20,2)</span>
      </div>
      <div ref={containerRef} style={{ width: '100%', flex: 1, minHeight: 0 }} />
    </div>
  )
}
