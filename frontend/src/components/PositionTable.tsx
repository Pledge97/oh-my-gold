import { useState } from 'react'
import { Button, DatePicker, Form, InputNumber, Modal, Table } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useStore } from '../store/useStore'
import { createPosition } from '../api/client'
import type { Position } from '../types'

interface FormValues {
  amount_g: number
  open_price: number
  open_date: dayjs.Dayjs
}

export function PositionTable() {
  const positions = useStore(s => s.positions)
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm<FormValues>()

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
    } finally {
      setLoading(false)
    }
  }

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
          <span style={{ color, fontFamily: "'Courier New', monospace", fontSize: 12, textShadow: `0 0 6px ${color}44` }}>
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
          <span style={{ color, fontFamily: "'Courier New', monospace", fontSize: 12, textShadow: `0 0 6px ${color}44` }}>
            {v >= 0 ? '+' : ''}{v.toFixed(2)}
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
          <span style={{ marginLeft: 8, fontSize: 10, color: (positions ?? []).length > 0 ? '#00ff88' : '#2a4a6a' }}>
            {(positions ?? []).length} 笔
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
        <Table<Position>
          dataSource={positions ?? []}
          columns={columns}
          rowKey="id"
          size="small"
          pagination={false}
          style={{ background: 'transparent' }}
        />
      </div>

      <Modal
        title={
          <span style={{ color: '#4fc3f7', letterSpacing: '0.08em', fontSize: 13 }}>
            手动建仓
          </span>
        }
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
        <Form
          form={form}
          layout="vertical"
          initialValues={{ amount_g: 20, open_date: dayjs() }}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入克数 (g)</span>}
            name="amount_g"
            rules={[{ required: true, message: '请输入克数' }, { type: 'number', min: 0.01, message: '克数必须大于0' }]}
          >
            <InputNumber
              style={{ width: '100%', background: '#060b14', borderColor: '#1a3a5c', color: '#c8d8e8' }}
              min={0.01}
              step={1}
              precision={2}
              suffix="g"
            />
          </Form.Item>

          <Form.Item
            label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入价格 (元/g)</span>}
            name="open_price"
            rules={[{ required: true, message: '请输入买入价格' }, { type: 'number', min: 0.01, message: '价格必须大于0' }]}
          >
            <InputNumber
              style={{ width: '100%', background: '#060b14', borderColor: '#1a3a5c', color: '#c8d8e8' }}
              min={0.01}
              step={0.01}
              precision={2}
              prefix="¥"
            />
          </Form.Item>

          <Form.Item
            label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入日期</span>}
            name="open_date"
            rules={[{ required: true, message: '请选择买入日期' }]}
          >
            <DatePicker
              style={{ width: '100%', background: '#060b14', borderColor: '#1a3a5c', color: '#c8d8e8' }}
              format="YYYY-MM-DD"
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
