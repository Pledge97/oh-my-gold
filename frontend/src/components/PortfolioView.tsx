import { useStore } from '../store/useStore'
import type { Lot } from '../types'

const SELL_FEE = 0.004

function pnlColor(val: number) {
  return val >= 0 ? '#ff4d4f' : '#00ff88'
}

export function PortfolioView() {
  const portfolio = useStore((s) => s.portfolio)
  const price = useStore((s) => s.price)

  const isEmpty = !portfolio || portfolio.total_amount_g === 0

  const pnlYuan = portfolio && price ? price * portfolio.total_amount_g - price * portfolio.total_amount_g * SELL_FEE - portfolio.total_cost : 0
  const pnlPct = portfolio && portfolio.total_cost > 0 ? pnlYuan / portfolio.total_cost : 0

  return (
    <div
      style={{
        background: '#0a1628',
        border: '1px solid #1a3a5c',
        borderRadius: 4,
        overflow: 'hidden',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0
      }}
    >
      <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        T仓组合
        {portfolio?.tp1_done && <span style={{ fontSize: 10, color: '#f0a500', border: '1px solid #f0a500', borderRadius: 2, padding: '0 4px' }}>止盈1</span>}
        {portfolio?.tp2_done && <span style={{ fontSize: 10, color: '#f0d060', border: '1px solid #f0d060', borderRadius: 2, padding: '0 4px' }}>止盈2</span>}
        {!isEmpty && (
          <span style={{ marginLeft: 'auto', display: 'flex', gap: 12, fontSize: 11 }}>
            <span>
              <span style={{ color: '#4a6a8a' }}>持仓 </span>
              <span style={{ color: '#c8d8e8', fontFamily: "'Courier New', monospace" }}>
                {portfolio!.total_amount_g.toFixed(1)}
                <span style={{ fontSize: 12, marginLeft: 3, opacity: 0.7, textTransform: 'none' }}>g</span>
              </span>
            </span>
            <span>
              <span style={{ color: '#4a6a8a' }}>均价 </span>
              <span style={{ color: '#f0d060', fontFamily: "'Courier New', monospace" }}>¥{portfolio!.avg_cost.toFixed(2)}</span>
            </span>
            <span style={{ color: pnlColor(pnlPct), fontFamily: "'Courier New', monospace" }}>
              <span style={{ color: '#4a6a8a' }}>盈亏 </span>
              {pnlYuan >= 0 ? '+' : ''}
              {pnlYuan.toFixed(2)}
              <span style={{ fontSize: 10, marginLeft: 3, opacity: 0.85 }}>
                ({pnlPct >= 0 ? '+' : ''}
                {(pnlPct * 100).toFixed(2)}%)
              </span>
            </span>
          </span>
        )}
      </div>

      {isEmpty ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2a4a6a', fontSize: 12 }}>暂无持仓</div>
      ) : (
        <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
          {/* 批次明细 */}
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid hsl(211, 56%, 23%)' }}>
                {['批次', '买入价', '克数', '盈亏', '买入时间'].map((h) => (
                  <th key={h} style={{ padding: '4px 8px', color: '#4fc3f7', fontWeight: 400, fontSize: 10, textAlign: 'left', letterSpacing: '0.06em' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {portfolio!.lots
                .filter((l: Lot) => l.status === 'OPEN')
                .map((lot: Lot) => {
                  const lotPnl = price ? (price - lot.open_price) * lot.amount_g - price * lot.amount_g * SELL_FEE : 0
                  const lotPnlPct = lot.open_price > 0 ? lotPnl / (lot.open_price * lot.amount_g) : 0
                  const lotColor = lotPnl >= 0 ? '#ff4d4f' : '#00ff88'
                  return (
                    <tr key={lot.lot_index} style={{ borderBottom: '1px solid #0d2035' }}>
                      <td style={{ padding: '5px 8px', color: '#f0a500' }}>第{lot.lot_index + 1}批</td>
                      <td style={{ padding: '5px 8px', color: '#f0d060', fontFamily: "'Courier New', monospace" }}>¥{lot.open_price.toFixed(2)}</td>
                      <td style={{ padding: '5px 8px', color: '#c8d8e8' }}>{lot.amount_g.toFixed(1)}g</td>
                      <td style={{ padding: '5px 8px', color: lotColor, fontFamily: "'Courier New', monospace" }}>
                        {lotPnl >= 0 ? '+' : ''}{lotPnl.toFixed(2)}
                        <span style={{ fontSize: 10, marginLeft: 3, opacity: 0.85 }}>
                          ({lotPnlPct >= 0 ? '+' : ''}{(lotPnlPct * 100).toFixed(2)}%)
                        </span>
                      </td>
                      <td style={{ padding: '5px 8px', color: '#4fc3f7' }}>
                        {new Date(lot.open_ts).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).replace(/\//g, '-').replace(/\s/g, ' ')}
                      </td>
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
