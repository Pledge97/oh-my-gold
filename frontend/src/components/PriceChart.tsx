import { useEffect, useRef } from 'react'
import { createChart, ColorType, LineStyle, type Time } from 'lightweight-charts'
import { useStore } from '../store/useStore'
import { MOBILE_PANEL_HEIGHT } from '../constants'

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
// Tooltip 距离鼠标指针的偏移量。
const TOOLTIP_OFFSET = 12
// Tooltip 预估宽度，用于避免贴近右侧时超出图表。
const TOOLTIP_WIDTH = 150
// Tooltip 预估高度，用于避免贴近底部时超出图表。
const TOOLTIP_HEIGHT = 112

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

/**
 * 把 Tooltip 定位到鼠标附近，并避免超出图表边界。
 *
 * @param tooltip Tooltip 元素。
 * @param x 鼠标在图表内的横坐标。
 * @param y 鼠标在图表内的纵坐标。
 * @param width 图表宽度。
 * @param height 图表高度。
 */
function placeTooltip(tooltip: HTMLDivElement, x: number, y: number, width: number, height: number) {
  const left = x + TOOLTIP_WIDTH + TOOLTIP_OFFSET > width ? x - TOOLTIP_WIDTH - TOOLTIP_OFFSET : x + TOOLTIP_OFFSET
  const top = y + TOOLTIP_HEIGHT + TOOLTIP_OFFSET > height ? y - TOOLTIP_HEIGHT - TOOLTIP_OFFSET : y + TOOLTIP_OFFSET
  tooltip.style.left = `${Math.max(TOOLTIP_OFFSET, left)}px`
  tooltip.style.top = `${Math.max(TOOLTIP_OFFSET, top)}px`
}

/**
 * 隐藏图表 Tooltip。
 *
 * @param tooltip Tooltip 元素。
 */
function hideTooltip(tooltip: HTMLDivElement | null) {
  if (tooltip) tooltip.style.display = 'none'
}

/** isMobile 为 true 时使用固定高度移动端布局。 */
export function PriceChart({ isMobile = false }: { isMobile?: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
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
      crosshair: {
        vertLine: { labelVisible: false },
        horzLine: { labelVisible: false }
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

    chart.subscribeCrosshairMove((param: any) => {
      const tooltip = tooltipRef.current
      const container = containerRef.current
      const candleSeries = candleRef.current
      if (!tooltip || !container || !candleSeries) return
      if (!param.point) {
        hideTooltip(tooltip)
        return
      }
      const isOutside =
        param.point.x < 0 ||
        param.point.y < 0 ||
        param.point.x > container.clientWidth ||
        param.point.y > container.clientHeight
      const candle = param.seriesData.get(candleSeries)
      if (isOutside || !candle) {
        hideTooltip(tooltip)
        return
      }
      tooltip.style.display = 'block'
      tooltip.innerHTML = `
        <div style="color:#4fc3f7;margin-bottom:6px;">${formatLocalChartTime(candle.time)}</div>
        <div>开：<span style="color:#f0d060">${candle.open.toFixed(2)}</span></div>
        <div>高：<span style="color:#ff4d4f">${candle.high.toFixed(2)}</span></div>
        <div>低：<span style="color:#00ff88">${candle.low.toFixed(2)}</span></div>
        <div>收：<span style="color:#f0d060">${candle.close.toFixed(2)}</span></div>
      `
      placeTooltip(tooltip, param.point.x, param.point.y, container.clientWidth, container.clientHeight)
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
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      border: '1px solid #1a3a5c',
      borderRadius: 4,
      ...(isMobile
        ? { height: MOBILE_PANEL_HEIGHT }
        : { flex: 1, minHeight: 0 }
      ),
    }}>
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
      <div
        ref={containerRef}
        onMouseLeave={() => hideTooltip(tooltipRef.current)}
        style={{ width: '100%', flex: 1, minHeight: 0, position: 'relative' }}
      >
        <div
          ref={tooltipRef}
          style={{
            position: 'absolute',
            display: 'none',
            zIndex: 10,
            width: TOOLTIP_WIDTH,
            padding: '8px 10px',
            border: '1px solid #1a3a5c',
            borderRadius: 4,
            background: 'rgba(6, 11, 20, 0.94)',
            boxShadow: '0 0 14px rgba(0, 212, 255, 0.18)',
            color: '#c8d8e8',
            fontSize: 11,
            lineHeight: 1.6,
            pointerEvents: 'none'
          }}
        />
      </div>
    </div>
  )
}
