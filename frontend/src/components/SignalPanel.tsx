import { Table, Tag } from 'antd'
import { useStore } from '../store/useStore'
import type { Signal } from '../types'

const TYPE_COLOR: Record<string, string> = {
  BUY: 'green',
  TAKE_PROFIT: 'blue',
  STOP_LOSS: 'red',
}

export function SignalPanel() {
  const signals = useStore(s => s.signals)
  const columns = [
    {
      title: '时间',
      dataIndex: 'ts',
      key: 'ts',
      render: (v: number) => new Date(v).toLocaleTimeString(),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (v: string) => <Tag color={TYPE_COLOR[v] ?? 'default'}>{v}</Tag>,
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      render: (v: number) => v.toFixed(2),
    },
    { title: '克数', dataIndex: 'amount_g', key: 'amount_g' },
    { title: '原因', dataIndex: 'reason', key: 'reason', ellipsis: true },
  ]
  return (
    <Table<Signal>
      dataSource={signals}
      columns={columns}
      rowKey="id"
      size="small"
      pagination={{ pageSize: 10 }}
    />
  )
}
