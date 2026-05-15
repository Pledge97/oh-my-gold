import { Table } from 'antd'
import { useStore } from '../store/useStore'
import type { Position } from '../types'

export function PositionTable() {
  const positions = useStore(s => s.positions)
  const columns = [
    {
      title: '开仓价',
      dataIndex: 'open_price',
      key: 'open_price',
      render: (v: number) => (
        <span style={{ color: '#f0d060', fontFamily: "'Courier New', monospace", fontSize: 12 }}>
          {v.toFixed(2)}
        </span>
      ),
    },
    {
      title: '克数',
      dataIndex: 'amount_g',
      key: 'amount_g',
      render: (v: number) => (
        <span style={{ color: '#c8d8e8', fontSize: 11 }}>{v}g</span>
      ),
    },
    {
      title: '盈亏%',
      dataIndex: 'pnl_pct',
      key: 'pnl_pct',
      render: (v: number) => {
        const color = v >= 0 ? '#00ff88' : '#ff4d4f'
        return (
          <span style={{
            color, fontFamily: "'Courier New', monospace", fontSize: 12,
            textShadow: `0 0 6px ${color}44`,
          }}>
            {v >= 0 ? '+' : ''}{(v * 100).toFixed(2)}%
          </span>
        )
      },
    },
    {
      title: '盈亏(元)',
      dataIndex: 'pnl_yuan',
      key: 'pnl_yuan',
      render: (v: number) => {
        const color = v >= 0 ? '#00ff88' : '#ff4d4f'
        return (
          <span style={{
            color, fontFamily: "'Courier New', monospace", fontSize: 12,
            textShadow: `0 0 6px ${color}44`,
          }}>
            {v >= 0 ? '+' : ''}{v.toFixed(2)}
          </span>
        )
      },
    },
  ]
  return (
    <div style={{
      background: '#0a1628',
      border: '1px solid #1a3a5c',
      borderRadius: 4,
      overflow: 'hidden',
    }}>
      <div className="panel-title">
        当前持仓
        <span style={{
          marginLeft: 'auto', fontSize: 10,
          color: (positions ?? []).length > 0 ? '#00ff88' : '#2a4a6a',
        }}>
          {(positions ?? []).length} 笔
        </span>
      </div>
      <Table<Position>
        dataSource={positions ?? []}
        columns={columns}
        rowKey="id"
        size="small"
        pagination={false}
        style={{ background: 'transparent' }}
      />
    </div>
  )
}
