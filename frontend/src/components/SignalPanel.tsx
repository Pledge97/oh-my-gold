import { Table, Tooltip } from 'antd'
import { useStore } from '../store/useStore'
import type { Signal } from '../types'

// Table body fills the remaining panel height so the header can stay fixed.
const TABLE_SCROLL_HEIGHT = '100%'

const TYPE_COLOR: Record<string, string> = {
  BUY: '#ff4d4f',
  ADD_LOT: '#ff8c00',
  TAKE_PROFIT: '#00d4ff',
  TAKE_PROFIT_1: '#00d4ff',
  TAKE_PROFIT_2: '#00d4ff',
  TAKE_PROFIT_TRAILING: '#00d4ff',
  STOP_LOSS: '#ff4d4f',
  STOP_LOSS_HALF: '#f0a500',
  STOP_LOSS_CLEAR: '#ff4d4f',
  TREND_CLEAR: '#ff4d4f'
}

const TYPE_LABEL: Record<string, string> = {
  BUY: '建仓',
  ADD_LOT: '加仓',
  TAKE_PROFIT: '止盈',
  TAKE_PROFIT_1: '止盈1',
  TAKE_PROFIT_2: '止盈2',
  TAKE_PROFIT_TRAILING: '追踪止盈',
  STOP_LOSS: '止损',
  STOP_LOSS_HALF: '减仓',
  STOP_LOSS_CLEAR: '清仓',
  TREND_CLEAR: '趋势清仓'
}

export function SignalPanel() {
  const signals = useStore((s) => s.signals)
  const portfolio = useStore((s) => s.portfolio)

  const nextBuyPrice = portfolio?.next_buy ?? null
  const tpPrice = portfolio?.next_tp ?? null
  const stopPrice = portfolio?.next_stop ?? null
  const columns = [
    {
      title: '时间',
      dataIndex: 'ts',
      key: 'ts',
      width: 80,
      render: (v: number) => <span style={{ color: '#4fc3f7', fontSize: 11 }}>{new Date(v).toLocaleTimeString('zh-CN', { hour12: false })}</span>
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 70,
      render: (v: string) => {
        const color = TYPE_COLOR[v] ?? '#888'
        return (
          <span
            style={{
              color,
              fontSize: 11,
              fontWeight: 700,
              textShadow: `0 0 6px ${color}66`
            }}
          >
            {TYPE_LABEL[v] ?? v}
          </span>
        )
      }
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      width: 75,
      render: (v: number) => <span style={{ color: '#f0d060', fontFamily: "'Courier New', monospace", fontSize: 12 }}>{v.toFixed(2)}</span>
    },
    {
      title: '克数',
      dataIndex: 'amount_g',
      key: 'amount_g',
      width: 55,
      render: (v: number) => <span style={{ color: '#c8d8e8', fontSize: 11 }}>{v}g</span>
    },
    {
      title: '盈亏',
      dataIndex: 'pnl_yuan',
      key: 'pnl_yuan',
      width: 70,
      render: (v: number | null | undefined, record: Signal) => {
        // 只有卖出类型的信号才显示盈亏
        const isSell = [
          'TAKE_PROFIT',
          'TAKE_PROFIT_1',
          'TAKE_PROFIT_2',
          'TAKE_PROFIT_TRAILING',
          'STOP_LOSS',
          'STOP_LOSS_HALF',
          'STOP_LOSS_CLEAR',
          'TREND_CLEAR'
        ].includes(record.type)
        if (!isSell || v == null) return <span style={{ color: '#4a6a8a', fontSize: 11 }}>-</span>
        const color = v >= 0 ? '#ff4d4f' : '#00ff88'
        return (
          <span
            style={{
              color,
              fontSize: 11,
              fontWeight: 600,
              fontFamily: "'Courier New', monospace",
              textShadow: `0 0 4px ${color}44`
            }}
          >
            {v >= 0 ? '+' : ''}
            {v.toFixed(2)}
          </span>
        )
      }
    },
    {
      title: '原因',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
      render: (v: string) => (
        <Tooltip title={v} color="#0a1628" styles={{ body: { color: '#c8d8e8', fontSize: 12, border: '1px solid #1a3a5c' } }}>
          <span style={{ color: '#6a8aaa', fontSize: 11, cursor: 'default' }}>{v}</span>
        </Tooltip>
      )
    }
  ]
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
      <div className="panel-title" style={{ flexWrap: 'wrap', gap: 8 }}>
        信号记录
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 10, fontSize: 10 }}>
          {nextBuyPrice ? (
            <span>
              <span style={{ color: '#4a6a8a' }}>买入 </span>
              <span style={{ color: '#00d4ff', fontFamily: "'Courier New', monospace" }}>{nextBuyPrice.toFixed(2)}</span>
            </span>
          ) : null}
          {tpPrice ? (
            <span>
              <span style={{ color: '#ff4d4f' }}>止盈 </span>
              <span style={{ color: '#ff4d4f', fontFamily: "'Courier New', monospace" }}>{tpPrice.toFixed(2)}</span>
            </span>
          ) : null}
          {stopPrice ? (
            <span>
              <span style={{ color: '#4a6a8a' }}>止损 </span>
              <span style={{ color: '#00ff88', fontFamily: "'Courier New', monospace" }}>{stopPrice.toFixed(2)}</span>
            </span>
          ) : null}
        </span>
      </div>
      {/* T仓持仓状态行：显示持仓量、均价、浮盈浮亏 */}
      {portfolio && portfolio.total_amount_g > 0 && (
        <div
          style={{
            padding: '4px 10px',
            fontSize: 11,
            borderBottom: '1px solid #1a3a5c',
            display: 'flex',
            gap: 12,
            color: '#6a8aaa',
            background: '#0d1e38'
          }}
        >
          <span>
            <span style={{ color: '#4a6a8a' }}>T仓 持仓 </span>
            <span style={{ color: '#c8d8e8', fontFamily: "'Courier New', monospace" }}>{portfolio.total_amount_g}g</span>
          </span>
          <span>
            <span style={{ color: '#4a6a8a' }}>均价 </span>
            <span style={{ color: '#f0d060', fontFamily: "'Courier New', monospace" }}>¥{portfolio.avg_cost?.toFixed(2)}</span>
          </span>
          <span>
            {/* 浮盈为正显示绿色，为负显示红色 */}
            <span style={{ color: '#4a6a8a' }}>浮盈 </span>
            <span
              style={{
                color: (portfolio.pnl_yuan ?? 0) >= 0 ? '#00ff88' : '#ff4d4f',
                fontFamily: "'Courier New', monospace"
              }}
            >
              {(portfolio.pnl_yuan ?? 0) >= 0 ? '+' : ''}
              {portfolio.pnl_yuan?.toFixed(0)}元 ({(portfolio.pnl_pct ?? 0) >= 0 ? '+' : ''}
              {((portfolio.pnl_pct ?? 0) * 100).toFixed(2)}%)
            </span>
          </span>
        </div>
      )}
      <div className="panel-table-body">
        <Table<Signal>
          dataSource={signals}
          columns={columns}
          rowKey="id"
          size="small"
          pagination={false}
          scroll={{ y: TABLE_SCROLL_HEIGHT }}
          sticky
          tableLayout="fixed"
          style={{ background: 'transparent' }}
        />
      </div>
    </div>
  )
}
