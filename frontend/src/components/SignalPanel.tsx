import { Table, Tooltip } from 'antd'
import { useStore } from '../store/useStore'
import type { Signal } from '../types'

// Table body fills the remaining panel height so the header can stay fixed.
const TABLE_SCROLL_HEIGHT = '100%'

const TYPE_COLOR: Record<string, string> = {
  BUY: '#ff4d4f',
  TAKE_PROFIT: '#00d4ff',
  STOP_LOSS: '#ff4d4f'
}

const TYPE_LABEL: Record<string, string> = {
  BUY: '买入',
  TAKE_PROFIT: '止盈',
  STOP_LOSS: '止损'
}

export function SignalPanel() {
  const signals = useStore((s) => s.signals)
  const indicators = useStore((s) => s.indicators)
  const portfolio = useStore((s) => s.portfolio)

  // V2 组合仓位触发节点
  const avgCost = portfolio?.avg_cost ?? 0
  const hasPosition = portfolio && portfolio.total_amount_g > 0

  // 下次买入：布林下轨（无持仓时）或上次买入价-1×ATR（加仓时）
  const nextBuyPrice = indicators?.bb_lower ?? null

  // 止盈：avg_cost × 1.006 / 0.996（扣手续费后净盈0.6%）
  const tpPrice = hasPosition ? avgCost * 1.006 / 0.996 : null

  // 止损：avg_cost × 0.975 / 0.996（扣手续费后净亏-2.5%，强制减半）
  const stopPrice = hasPosition ? avgCost * 0.975 / 0.996 : null
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
