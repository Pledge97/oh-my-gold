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
      render: (v: number) => v.toFixed(2),
    },
    { title: '克数', dataIndex: 'amount_g', key: 'amount_g' },
    {
      title: '盈亏%',
      dataIndex: 'pnl_pct',
      key: 'pnl_pct',
      render: (v: number) => {
        const color = v >= 0 ? '#52c41a' : '#ff4d4f'
        return <span style={{ color }}>{(v * 100).toFixed(2)}%</span>
      },
    },
    {
      title: '盈亏(元)',
      dataIndex: 'pnl_yuan',
      key: 'pnl_yuan',
      render: (v: number) => {
        const color = v >= 0 ? '#52c41a' : '#ff4d4f'
        return <span style={{ color }}>{v.toFixed(2)}</span>
      },
    },
  ]
  return (
    <Table<Position>
      dataSource={positions}
      columns={columns}
      rowKey="id"
      size="small"
      pagination={false}
    />
  )
}
