import { useEffect, useState } from 'react'
import { Button, DatePicker, Form, InputNumber, Modal, Table } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useStore, DbPosition } from '../store/useStore'
import { createPosition, fetchPositions } from '../api/client'

const SELL_FEE = 0.004

interface FormValues {
  amount_g: number
  open_price: number
  open_date: dayjs.Dayjs
}

export function PositionTable() {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm<FormValues>()
  const { lastSignalTs, dbPositions, setDbPositions, price } = useStore()

  const reload = () => fetchPositions('OPEN').then(setDbPositions)

  useEffect(() => { reload() }, [])
  useEffect(() => { if (lastSignalTs > 0) reload() }, [lastSignalTs])

  const handleSubmit = async () => {
    const values = await form.validateFields()
    setLoading(true)
    try {
      await createPosition({
        amount_g: values.amount_g,
        open_price: values.open_price,
        open_date: values.open_date.format('YYYY-MM-DD'),
      })
      form.resetFields()
      setOpen(false)
      reload()
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '开仓日期',
      dataIndex: 'open_ts',
      key: 'open_ts',
      render: (v: number) => (
        <span style={{ color: '#4fc3f7', fontSize: 11 }}>
          {new Date(v).toLocaleDateString('zh-CN')}
        </span>
      ),
    },
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
      title: '盈亏(元)',
      key: 'pnl',
      render: (_: unknown, row: DbPosition) => {
        if (!price || price === 0) return <span style={{ color: '#2a4a6a' }}>—</span>
        const pnl = (price - row.open_price) * row.amount_g - price * row.amount_g * SELL_FEE
        const color = pnl >= 0 ? '#00ff88' : '#ff4d4f'
        return (
          <span style={{ color, fontFamily: "'Courier New', monospace", fontSize: 12, textShadow: `0 0 6px ${color}44` }}>
            {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}
          </span>
        )
      },
    },
    {
      title: '盈亏%',
      key: 'pnl_pct',
      render: (_: unknown, row: DbPosition) => {
        if (!price || price === 0) return <span style={{ color: '#2a4a6a' }}>—</span>
        const pct = (price - row.open_price) / row.open_price
        const color = pct >= 0 ? '#00ff88' : '#ff4d4f'
        return (
          <span style={{ color, fontFamily: "'Courier New', monospace", fontSize: 12 }}>
            {pct >= 0 ? '+' : ''}{(pct * 100).toFixed(2)}%
          </span>
        )
      },
    },
  ]

  return (
    <>
      <div style={{ background: '#0a1628', border: '1px solid #1a3a5c', borderRadius: 4, overflow: 'hidden' }}>
        <div className="panel-title" style={{ display: 'flex', alignItems: 'center' }}>
          当前持仓
          <span style={{ marginLeft: 8, fontSize: 10, color: dbPositions.length > 0 ? '#00ff88' : '#2a4a6a' }}>
            {dbPositions.length} 笔
          </span>
          <Button
            size="small"
            icon={<PlusOutlined />}
            onClick={() => setOpen(true)}
            style={{
              marginLeft: 'auto',
              background: 'transparent',
              border: '1px solid #1a3a5c',
              color: '#4fc3f7',
              fontSize: 11,
              height: 22,
              padding: '0 8px',
            }}
          >
            手动建仓
          </Button>
        </div>
        <Table<DbPosition>
          dataSource={dbPositions}
          columns={columns}
          rowKey="id"
          size="small"
          pagination={false}
          style={{ background: 'transparent' }}
        />
      </div>

      <Modal
        title={<span style={{ color: '#4fc3f7', letterSpacing: '0.08em', fontSize: 13 }}>手动建仓</span>}
        open={open}
        onOk={handleSubmit}
        onCancel={() => { setOpen(false); form.resetFields() }}
        confirmLoading={loading}
        okText="确认建仓"
        cancelText="取消"
        styles={{
          content: { background: '#0a1628', border: '1px solid #1a3a5c' },
          header: { background: '#0a1628', borderBottom: '1px solid #1a3a5c' },
          footer: { background: '#0a1628', borderTop: '1px solid #1a3a5c' },
          mask: { backdropFilter: 'blur(2px)' },
        }}
      >
        <Form form={form} layout="vertical" initialValues={{ amount_g: 20, open_date: dayjs() }} style={{ marginTop: 16 }}>
          <Form.Item
            label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入克数 (g)</span>}
            name="amount_g"
            rules={[{ required: true, message: '请输入克数' }, { type: 'number', min: 0.01 }]}
          >
            <InputNumber style={{ width: '100%', background: '#060b14', borderColor: '#1a3a5c', color: '#c8d8e8' }} min={0.01} step={1} precision={2} suffix="g" />
          </Form.Item>
          <Form.Item
            label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入价格 (元/g)</span>}
            name="open_price"
            rules={[{ required: true, message: '请输入买入价格' }, { type: 'number', min: 0.01 }]}
          >
            <InputNumber style={{ width: '100%', background: '#060b14', borderColor: '#1a3a5c', color: '#c8d8e8' }} min={0.01} step={0.01} precision={2} prefix="¥" />
          </Form.Item>
          <Form.Item
            label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入日期</span>}
            name="open_date"
            rules={[{ required: true, message: '请选择买入日期' }]}
          >
            <DatePicker style={{ width: '100%', background: '#060b14', borderColor: '#1a3a5c', color: '#c8d8e8' }} format="YYYY-MM-DD" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
