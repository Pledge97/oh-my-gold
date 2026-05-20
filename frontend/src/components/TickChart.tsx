import { useEffect, useRef } from 'react'
import { createChart, ColorType, LineStyle, type Time } from 'lightweight-charts'
import { useStore } from '../store/useStore'
import { fetchTickPrices } from '../api/client'
import { MOBILE_PANEL_HEIGHT } from '../constants'

// 图表横轴显示使用的本地化语言。
const CHART_LOCALE = 'zh-CN'
// 容器宽度尚未计算完成时的兜底宽度。
const DEFAULT_CHART_WIDTH = 600
// 容器高度尚未计算完成时的兜底高度。
const DEFAULT_CHART_HEIGHT = 200
// 单个 tick 最小间距，允许 24 小时高频数据压缩到一屏。
const MIN_TICK_BAR_SPACING = 0.001
// 第一条 tick 前保留的逻辑边距。
const LEFT_LOGICAL_PADDING = 0.5
// 最新 tick 后保留的逻辑边距。
const RIGHT_LOGICAL_PADDING = 1.5
// Tooltip 距离鼠标指针的偏移量。
const TOOLTIP_OFFSET = 12
// Tooltip 预估宽度，用于避免贴近右侧时超出图表。
const TOOLTIP_WIDTH = 150
// Tooltip 预估高度，用于避免贴近底部时超出图表。
const TOOLTIP_HEIGHT = 72

/**
 * 按本地时区格式化实时图横轴时间。
 *
 * @param time lightweight-charts 传入的时间值。
 * @returns 本地时间文本。
 */
function formatLocalTickTime(time: Time) {
  if (typeof time === 'number') {
    return new Date(time * 1000).toLocaleTimeString(CHART_LOCALE, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  }
  if (typeof time === 'string') {
    return new Date(`${time}T00:00:00`).toLocaleDateString(CHART_LOCALE)
  }
  return new Date(time.year, time.month - 1, time.day).toLocaleDateString(CHART_LOCALE)
}

/**
 * 设置横轴可见逻辑范围，让 24 小时 tick 数据默认占满图表宽度。
 *
 * @param chart lightweight-charts 图表实例。
 * @param dataLength tick 数据条数。
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function fillTickTimeScale(chart: any, dataLength: number) {
  if (!chart || dataLength <= 0) return
  const chartWidth = chart.timeScale().width() || DEFAULT_CHART_WIDTH
  const visibleLogicalCount = dataLength + LEFT_LOGICAL_PADDING + RIGHT_LOGICAL_PADDING
  chart.timeScale().applyOptions({
    barSpacing: Math.max(MIN_TICK_BAR_SPACING, chartWidth / visibleLogicalCount),
    minBarSpacing: MIN_TICK_BAR_SPACING,
  })
  chart.timeScale().setVisibleLogicalRange({
    from: -LEFT_LOGICAL_PADDING,
    to: dataLength - 1 + RIGHT_LOGICAL_PADDING,
  })
}

/**
 * 按容器当前尺寸刷新图表，并在布局稳定后重新铺满横轴。
 *
 * @param chart lightweight-charts 图表实例。
 * @param container 图表容器元素。
 * @param dataLength tick 数据条数。
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function resizeTickChart(chart: any, container: HTMLDivElement, dataLength: number) {
  chart.applyOptions({
    width: container.clientWidth || DEFAULT_CHART_WIDTH,
    height: container.clientHeight || DEFAULT_CHART_HEIGHT,
  })
  return requestAnimationFrame(() => fillTickTimeScale(chart, dataLength))
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
export function TickChart({ isMobile = false }: { isMobile?: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
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
  const dataLengthRef = useRef(0)

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
      localization: {
        locale: CHART_LOCALE,
        timeFormatter: formatLocalTickTime,
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: true,
        borderColor: '#1a3a5c',
        tickMarkFormatter: formatLocalTickTime,
        minBarSpacing: MIN_TICK_BAR_SPACING,
      },
      rightPriceScale: { borderColor: '#1a3a5c' },
      crosshair: {
        vertLine: { color: '#00d4ff44', labelVisible: false },
        horzLine: { color: '#00d4ff44', labelVisible: false }
      },
      width: containerRef.current.clientWidth || DEFAULT_CHART_WIDTH,
      height: containerRef.current.clientHeight || DEFAULT_CHART_HEIGHT,
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

    chart.subscribeCrosshairMove((param: any) => {
      const tooltip = tooltipRef.current
      const container = containerRef.current
      const lineSeries = lineRef.current
      if (!tooltip || !container || !lineSeries) return
      if (!param.point) {
        hideTooltip(tooltip)
        return
      }
      const isOutside =
        param.point.x < 0 ||
        param.point.y < 0 ||
        param.point.x > container.clientWidth ||
        param.point.y > container.clientHeight
      const point = param.seriesData.get(lineSeries)
      if (isOutside || !point) {
        hideTooltip(tooltip)
        return
      }
      tooltip.style.display = 'block'
      tooltip.innerHTML = `
        <div style="color:#4fc3f7;margin-bottom:6px;">${formatLocalTickTime(point.time)}</div>
        <div>价格：<span style="color:#f0d060">${point.value.toFixed(2)}</span></div>
      `
      placeTooltip(tooltip, param.point.x, param.point.y, container.clientWidth, container.clientHeight)
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
      dataLengthRef.current = points.length
      fillTickTimeScale(chart, points.length)
    })

    let resizeFrameId = 0
    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        if (resizeFrameId) cancelAnimationFrame(resizeFrameId)
        resizeFrameId = resizeTickChart(chart, containerRef.current, dataLengthRef.current)
      }
    })
    ro.observe(containerRef.current)

    return () => {
      if (resizeFrameId) cancelAnimationFrame(resizeFrameId)
      chart.remove()
      ro.disconnect()
    }
  }, [])

  // 实时追加新 tick
  useEffect(() => {
    if (!price || !lineRef.current) return
    const nowSec = Math.floor(Date.now() / 1000)
    const nowMs = nowSec * 1000
    if (nowMs <= lastTsRef.current) return
    lastTsRef.current = nowMs
    lineRef.current.update({ time: nowSec as unknown as `${number}`, value: price })
    dataLengthRef.current += 1
    fillTickTimeScale(chartRef.current, dataLengthRef.current)
  }, [price])

  // 实时更新布林带
  useEffect(() => {
    if (!indicators || !price) return
    const nowSec = Math.floor(Date.now() / 1000) as unknown as `${number}`
    bbUpperRef.current?.update({ time: nowSec, value: indicators.bb_upper })
    bbLowerRef.current?.update({ time: nowSec, value: indicators.bb_lower })
  }, [indicators, price])

  return (
    <div style={{
      border: '1px solid #1a3a5c',
      borderRadius: 4,
      display: 'flex',
      flexDirection: 'column',
      ...(isMobile
        ? { height: MOBILE_PANEL_HEIGHT }
        : { flex: 1, minHeight: 0 }
      ),
    }}>
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
