import { useStore } from '../store/useStore'
import type { Lot } from '../types'

const SELL_FEE = 0.004

function pnlColor(val: number) {
  return val >= 0 ? '#ff4d4f' : '#00ff88'
}

function pnlGlow(val: number) {
  return val >= 0 ? '0 0 6px rgba(255,77,79,0.4)' : '0 0 6px rgba(0,255,136,0.4)'
}

export function PortfolioView() {
  const portfolio = useStore(s => s.portfolio)
  const price = useStore(s => s.price)

  const isEmpty = !portfolio || portfolio.total_amount_g === 0

  const pnlYuan = portfolio && price
    ? price * portfolio.total_amount_g - price * portfolio.total_amount_g * SELL_FEE - portfolio.total_cost
    : 0
  const pnlPct = portfolio && portfolio.total_cost > 0 ? pnlYuan / portfolio.total_cost : 0

  return (
    <div style={{
      background: '#0a1628',
      border: '1px solid #1a3a5c',
      borderRadius: 4,
      overflow: 'hidden',
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      minHeight: 0,
    }}>
      <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        T仓组合
        {portfolio?.tp1_done && (
          <span style={{ fontSize: 10, color: '#f0a500', border: '1px solid #f0a500', borderRadius: 2, padding: '0 4px' }}>止盈1</span>
        )}
        {portfolio?.tp2_done && (
          <span style={{ fontSize: 10, color: '#f0d060', border: '1px solid #f0d060', borderRadius: 2, padding: '0 4px' }}>止盈2</span>
        )}
        {!isEmpty && (
          <span style={{ marginLeft: 'auto', fontSize: 11, fontFamily: "'Courier New', monospace", color: pnlColor(pnlPct), textShadow: pnlGlow(pnlPct) }}>
            {pnlPct >= 0 ? '+' : ''}{(pnlPct * 100).toFixed(2)}%
            <span style={{ color: '#888', marginLeft: 6 }}>
              ({pnlYuan >= 0 ? '+' : ''}{pnlYuan.toFixed(2)}元)
            </span>
          </span>
        )}
      </div>

      {isEmpty ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2a4a6a', fontSize: 12 }}>
          暂无持仓
        </div>
      ) : (
        <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
          {/* 汇总行 */}
          <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid #1a3a5c' }}>
            {[
              { label: '总持仓', value: `${portfolio!.total_amount_g.toFixed(1)}g` },
              { label: '均成本', value: `¥${portfolio!.avg_cost.toFixed(2)}` },
              { label: '批次', value: `${portfolio!.lots.filter((l: Lot) => l.status === 'OPEN').length}批` },
            ].map(({ label, value }) => (
              <div key={label} style={{ flex: 1, padding: '6px 10px', borderRight: '1px solid #1a3a5c' }}>
                <div style={{ fontSize: 9, color: '#4fc3f7', letterSpacing: '0.08em', marginBottom: 2 }}>{label}</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#c8d8e8', fontFamily: "'Courier New', monospace" }}>{value}</div>
              </div>
            ))}
          </div>

          {/* 批次明细 */}
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #1a3a5c' }}>
                {['批次', '买入价', '克数', '时间'].map(h => (
                  <th key={h} style={{ padding: '4px 8px', color: '#4fc3f7', fontWeight: 400, fontSize: 10, textAlign: 'left', letterSpacing: '0.06em' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {portfolio!.lots.filter((l: Lot) => l.status === 'OPEN').map((lot: Lot) => (
                <tr key={lot.lot_index} style={{ borderBottom: '1px solid #0d2035' }}>
                  <td style={{ padding: '5px 8px', color: '#f0a500' }}>第{lot.lot_index + 1}批</td>
                  <td style={{ padding: '5px 8px', color: '#f0d060', fontFamily: "'Courier New', monospace" }}>¥{lot.open_price.toFixed(2)}</td>
                  <td style={{ padding: '5px 8px', color: '#c8d8e8' }}>{lot.amount_g.toFixed(1)}g</td>
                  <td style={{ padding: '5px 8px', color: '#4fc3f7' }}>{new Date(lot.open_ts).toLocaleTimeString('zh-CN', { hour12: false })}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* 下次触发价 */}
          {(portfolio!.next_buy || portfolio!.next_tp || portfolio!.next_stop) && (
            <div style={{ display: 'flex', gap: 0, borderTop: '1px solid #1a3a5c' }}>
              {portfolio!.next_buy && (
                <div style={{ flex: 1, padding: '5px 8px', borderRight: '1px solid #1a3a5c' }}>
                  <div style={{ fontSize: 9, color: '#4fc3f7', marginBottom: 1 }}>加仓价</div>
                  <div style={{ fontSize: 11, color: '#00ff88', fontFamily: "'Courier New', monospace" }}>¥{portfolio!.next_buy.toFixed(2)}</div>
                </div>
              )}
              {portfolio!.next_tp && (
                <div style={{ flex: 1, padding: '5px 8px', borderRight: '1px solid #1a3a5c' }}>
                  <div style={{ fontSize: 9, color: '#4fc3f7', marginBottom: 1 }}>止盈价</div>
                  <div style={{ fontSize: 11, color: '#ff4d4f', fontFamily: "'Courier New', monospace" }}>¥{portfolio!.next_tp.toFixed(2)}</div>
                </div>
              )}
              {portfolio!.next_stop && (
                <div style={{ flex: 1, padding: '5px 8px' }}>
                  <div style={{ fontSize: 9, color: '#4fc3f7', marginBottom: 1 }}>止损价</div>
                  <div style={{ fontSize: 11, color: '#f0a500', fontFamily: "'Courier New', monospace" }}>¥{portfolio!.next_stop.toFixed(2)}</div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
