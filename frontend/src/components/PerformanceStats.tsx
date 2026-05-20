import { useStore } from '../store/useStore'

interface StatCardProps {
  /** 统计项标签。 */
  label: string
  /** 统计项数值文本。 */
  value: string
  /** 数值颜色，默认 #c8d8e8。 */
  color?: string
  /** 数值单位。 */
  unit?: string
  /** 是否手机端布局。 */
  isMobile?: boolean
}

function StatCard({ label, value, color = '#c8d8e8', unit, isMobile = false }: StatCardProps) {
  return (
    <div style={{
      background: '#0a1628',
      border: '1px solid #1a3a5c',
      borderRadius: 4,
      padding: '10px 14px',
      flex: isMobile ? '0 0 calc(33.333% - 6px)' : 1,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* 顶部装饰线 */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, transparent, ${color}66, transparent)`,
      }} />
      <div style={{
        fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em',
        textTransform: 'uppercase', marginBottom: 6,
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 20, fontWeight: 700, color,
        fontFamily: "'Courier New', monospace",
        textShadow: `0 0 10px ${color}44`,
        lineHeight: 1,
      }}>
        {value}
        {unit && <span style={{ fontSize: 11, color: '#4a6a8a', marginLeft: 3 }}>{unit}</span>}
      </div>
    </div>
  )
}

export function PerformanceStats({ isMobile = false }: { isMobile?: boolean }) {
  const perf = useStore(s => s.performance)
  if (!perf) return null

  const pnlColor = perf.total_pnl_yuan >= 0 ? '#ff4d4f' : '#00ff88'

  return (
    <div style={{
      background: '#0a1628',
      border: '1px solid #1a3a5c',
      borderRadius: 4,
      overflow: 'hidden',
      flexShrink: 0,
    }}>
      <div className="panel-title">绩效统计</div>
      <div style={{ display: 'flex', gap: 8, padding: 10, ...(isMobile && { flexWrap: 'wrap' }) }}>
        <StatCard label="总交易" value={String(perf.total_trades)} color="#00d4ff" unit="笔" isMobile={isMobile} />
        <StatCard
          label="T仓盈亏"
          value={(perf.total_pnl_yuan >= 0 ? '+' : '') + perf.total_pnl_yuan.toFixed(2)}
          color={pnlColor}
          unit="元"
          isMobile={isMobile}
        />
        <StatCard
          label="胜率"
          value={(perf.win_rate * 100).toFixed(1)}
          color="#f0a500"
          unit="%"
          isMobile={isMobile}
        />
        <StatCard
          label="平均盈利"
          value={'+' + perf.avg_win_yuan.toFixed(2)}
          color="#ff4d4f"
          unit="元"
          isMobile={isMobile}
        />
        <StatCard
          label="平均亏损"
          value={perf.avg_loss_yuan.toFixed(2)}
          color="#00ff88"
          unit="元"
          isMobile={isMobile}
        />
        <StatCard
          label="盈亏比"
          value={perf.profit_loss_ratio.toFixed(2)}
          color="#00d4ff"
          isMobile={isMobile}
        />
      </div>
    </div>
  )
}
