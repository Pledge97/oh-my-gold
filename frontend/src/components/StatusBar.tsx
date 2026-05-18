import { Typography } from 'antd'
import { useStore } from '../store/useStore'

const STATE_COLOR: Record<string, string> = {
  OSCILLATION: '#00d4ff',
  TREND_UP: '#00ff88',
  TREND_DOWN: '#ff4d4f',
  TREND_DECAY: '#f0a500'
}

const STATE_LABEL: Record<string, string> = {
  OSCILLATION: '震荡',
  TREND_UP: '上涨趋势',
  TREND_DOWN: '下跌趋势',
  TREND_DECAY: '趋势衰减'
}

export function StatusBar() {
  const { price, marketState, cbActive, cbLevel, dbPositions, portfolio, isMarketOpen } = useStore()
  const stateColor = STATE_COLOR[marketState] ?? '#888'

  // 底仓汇总
  const baseCost = dbPositions.reduce((sum, pos) => sum + pos.open_price * pos.amount_g, 0)
  const baseAmountG = dbPositions.reduce((sum, pos) => sum + pos.amount_g, 0)

  // T仓汇总（来自 WebSocket portfolio）
  const tAmountG = portfolio?.total_amount_g ?? 0
  const tCost = portfolio?.total_cost ?? 0

  // 合并
  const totalAmountG = baseAmountG + tAmountG
  const totalCost = baseCost + tCost
  const totalMarketValue = price ? price * totalAmountG : 0
  const totalPnl = price ? totalMarketValue - price * totalAmountG * 0.004 - totalCost : 0
  const totalPnlPct = totalCost > 0 ? totalPnl / totalCost : 0

  return (
    <div
      style={{
        padding: '10px 20px',
        background: 'linear-gradient(90deg, #060b14 0%, #0a1628 50%, #060b14 100%)',
        borderBottom: '1px solid #1a3a5c',
        display: 'flex',
        alignItems: 'center',
        gap: 24,
        position: 'relative',
        overflow: 'hidden',
        flexShrink: 0
      }}
    >
      {/* 左侧装饰线 */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: 3,
          background: 'linear-gradient(180deg, transparent, #00d4ff, transparent)'
        }}
      />

      {/* 金价 */}
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
        <span style={{ fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em', textTransform: 'uppercase' }}>AU积存金</span>
        <Typography.Text
          className="price-value"
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: '#f0d060',
            fontFamily: "'Courier New', monospace",
            textShadow: '0 0 12px rgba(240,208,96,0.4)',
            letterSpacing: '0.02em'
          }}
        >
          ¥{price.toFixed(2)}
          <span style={{ fontSize: 13, color: '#888', marginLeft: 4 }}>/g</span>
        </Typography.Text>
      </div>

      {/* 熔断 */}
      {cbActive && (
        <>
          <div style={{ width: 1, height: 36, background: '#1a3a5c' }} />
          <div
            style={{
              padding: '4px 12px',
              background: 'rgba(255,77,79,0.15)',
              border: '1px solid #ff4d4f',
              borderRadius: 4,
              color: '#ff4d4f',
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: '0.08em',
              boxShadow: '0 0 12px rgba(255,77,79,0.3)',
              animation: 'numPulse 1s ease-in-out infinite'
            }}
          >
            ⚠ 熔断 L{cbLevel}
          </div>
        </>
      )}

      <div style={{ width: 1, height: 36, background: '#1a3a5c' }} />

      {/* 持仓克数 */}
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.4 }}>
        <span style={{ fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em', textTransform: 'uppercase' }}>持仓克数</span>
        <span style={{ fontSize: 16, fontWeight: 700, color: '#c8d8e8', fontFamily: "'Courier New', monospace" }}>
          {totalAmountG.toFixed(1)}
          <span style={{ fontSize: 12, marginLeft: 3, opacity: 0.7 }}>g</span>
        </span>
      </div>

      <div style={{ width: 1, height: 36, background: '#1a3a5c' }} />

      {/* 持仓金额 */}
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.4 }}>
        <span style={{ fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em', textTransform: 'uppercase' }}>持仓金额</span>
        <span style={{ fontSize: 16, fontWeight: 700, color: '#f0d060', fontFamily: "'Courier New', monospace" }}>
          {totalMarketValue.toFixed(0)}
          <span style={{ fontSize: 12, marginLeft: 3, opacity: 0.7 }}>元</span>
        </span>
      </div>

      <div style={{ width: 1, height: 36, background: '#1a3a5c' }} />

      {/* 持仓盈亏 */}
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.4 }}>
        <span style={{ fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em', textTransform: 'uppercase' }}>持仓盈亏</span>
        <span
          style={{
            fontSize: 16,
            fontWeight: 700,
            color: totalPnl >= 0 ? '#ff4d4f' : '#00ff88',
            textShadow: totalPnl >= 0 ? '0 0 8px rgba(255,77,79,0.4)' : '0 0 8px rgba(0,255,136,0.4)',
            fontFamily: "'Courier New', monospace"
          }}
        >
          {totalPnl >= 0 ? '+' : ''}
          {totalPnl.toFixed(2)} 元
          <span style={{ fontSize: 12, marginLeft: 6, opacity: 0.85 }}>
            ({totalPnlPct >= 0 ? '+' : ''}
            {(totalPnlPct * 100).toFixed(2)}%)
          </span>
        </span>
      </div>

      {/* 右侧：市场状态 + 时间 */}
      <div style={{ marginLeft: 'auto', textAlign: 'right', display: 'flex', alignItems: 'center', gap: 16 }}>
        {/* 市场状态 */}
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.4, textAlign: 'right' }}>
          <span style={{ fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em', textTransform: 'uppercase' }}>行情</span>
          <span
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: stateColor,
              textShadow: `0 0 8px ${stateColor}66`,
              letterSpacing: '0.05em'
            }}
          >
            {STATE_LABEL[marketState] ?? marketState}
          </span>
        </div>
        <div style={{ width: 1, height: 36, background: '#1a3a5c' }} />
        {/* 时间 */}
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.4, textAlign: 'right' }}>
          <span style={{ fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em', textTransform: 'uppercase' }}>市场状态</span>
          <span
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: stateColor,
              textShadow: `0 0 8px ${stateColor}66`,
              letterSpacing: '0.05em'
            }}
          >
            {isMarketOpen ? '开市' : '休市'}
          </span>
        </div>
      </div>
    </div>
  )
}
