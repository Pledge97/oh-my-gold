import { useEffect, useState } from 'react'
import { Button, DatePicker, Form, InputNumber, Modal, Table } from 'antd'
import { PlusOutlined, DollarOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useStore, DbPosition } from '../store/useStore'
import { createPosition, closePosition, fetchPositions } from '../api/client'

const SELL_FEE = 0.004

interface BuyFormValues {
  amount_g: number
  open_price: number
  open_date: dayjs.Dayjs
}

interface SellFormValues {
  close_price: number
  close_date: dayjs.Dayjs
}

export function PositionTable() {
  const [buyOpen, setBuyOpen] = useState(false)
  const [sellOpen, setSellOpen] = useState(false)
  const [sellingPos, setSellingPos] = useState<DbPosition | null>(null)
  const [loading, setLoading] = useState(false)
  const [buyForm] = Form.useForm<BuyFormValues>()
  const [sellForm] = Form.useForm<SellFormValues>()
  const { lastSignalTs, dbPositions, setDbPositions, price } = useStore()

  const reload = () => fetchPositions('OPEN').then(setDbPositions)

  useEffect(() => { reload() }, [])
  useEffect(() => { if (lastSignalTs > 0) reload() }, [lastSignalTs])

  const handleBuy = async () => {
    const values = await buyForm.validateFields()
    setLoading(true)
    try {
      await createPosition({
        amount_g: values.amount_g,
        open_price: values.open_price,
        open_date: values.open_date.format('YYYY-MM-DD'),
      })
      buyForm.resetFields()
      setBuyOpen(false)
      reload()
    } finally {
      setLoading(false)
    }
  }

  const openSell = (pos: DbPosition) => {
    setSellingPos(pos)
    sellForm.setFieldsValue({
      close_price: price || pos.open_price,
      close_date: dayjs(),
    })
    setSellOpen(true)
  }

  const handleSell = async () => {
    if (!sellingPos) return
    const values = await sellForm.validateFields()
    setLoading(true)
    try {
      await closePosition(sellingPos.id, {
        close_price: values.close_price,
        close_date: values.close_date.format('YYYY-MM-DD HH:mm'),
      })
      sellForm.resetFields()
      setSellOpen(false)
      setSellingPos(null)
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
      title: '盈亏',
      key: 'pnl',
      render: (_: unknown, row: DbPosition) => {
        if (!price || price === 0) return <span style={{ color: '#2a4a6a' }}>—</span>
        const pnl = (price - row.open_price) * row.amount_g - price * row.amount_g * SELL_FEE
        const pct = pnl / (row.open_price * row.amount_g)
        const color = pnl >= 0 ? '#00ff88' : '#ff4d4f'
        return (
          <span style={{ color, fontFamily: "'Courier New', monospace", fontSize: 12, textShadow: `0 0 6px ${color}44` }}>
            {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}
            <span style={{ fontSize: 10, marginLeft: 4, opacity: 0.8 }}>
              ({pct >= 0 ? '+' : ''}{(pct * 100).toFixed(2)}%)
            </span>
          </span>
        )
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 50,
      render: (_: unknown, row: DbPosition) => (
        <Button
          type="text"
          size="small"
          icon={<DollarOutlined />}
          onClick={() => openSell(row)}
          style={{ color: '#ff4d4f', padding: 0 }}
          title="卖出"
        />
      ),
    },
  ]

  const modalStyle = {
    content: { background: '#0a1628', border: '1px solid #1a3a5c' },
    header: { background: '#0a1628', borderBottom: '1px solid #1a3a5c' },
    footer: { background: '#0a1628', borderTop: '1px solid #1a3a5c' },
    mask: { backdropFilter: 'blur(2px)' },
  }

  const inputStyle = { width: '100%', background: '#060b14', borderColor: '#1a3a5c', color: '#c8d8e8' }

  return (
    <>
      <div style={{ background: '#0a1628', border: '1px solid #1a3a5c', borderRadius: 4, overflow: 'hidden', flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div className="panel-title" style={{ display: 'flex', alignItems: 'center' }}>
          当前持仓
          <span style={{ marginLeft: 8, fontSize: 10, color: dbPositions.length > 0 ? '#00ff88' : '#2a4a6a' }}>
            {dbPositions.length} 笔
          </span>
          <Button
            size="small"
            icon={<PlusOutlined />}
            onClick={() => setBuyOpen(true)}
            style={{ marginLeft: 'auto', background: 'transparent', border: '1px solid #1a3a5c', color: '#4fc3f7', fontSize: 11, height: 22, padding: '0 8px' }}
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

      {/* 建仓弹窗 */}
      <Modal
        title={<span style={{ color: '#4fc3f7', letterSpacing: '0.08em', fontSize: 13 }}>手动建仓</span>}
        open={buyOpen}
        onOk={handleBuy}
        onCancel={() => { setBuyOpen(false); buyForm.resetFields() }}
        confirmLoading={loading}
        okText="确认建仓"
        cancelText="取消"
        styles={modalStyle}
      >
        <Form form={buyForm} layout="vertical" initialValues={{ amount_g: 20, open_date: dayjs() }} style={{ marginTop: 16 }}>
          <Form.Item label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入克数 (g)</span>} name="amount_g" rules={[{ required: true }, { type: 'number', min: 0.01 }]}>
            <InputNumber style={inputStyle} min={0.01} step={1} precision={2} suffix="g" />
          </Form.Item>
          <Form.Item label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入价格 (元/g)</span>} name="open_price" rules={[{ required: true }, { type: 'number', min: 0.01 }]}>
            <InputNumber style={inputStyle} min={0.01} step={0.01} precision={2} prefix="¥" />
          </Form.Item>
          <Form.Item label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入日期</span>} name="open_date" rules={[{ required: true }]}>
            <DatePicker style={inputStyle} format="YYYY-MM-DD" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 卖出弹窗 */}
      <Modal
        title={
          <span style={{ color: '#ff4d4f', letterSpacing: '0.08em', fontSize: 13 }}>
            卖出持仓
            {sellingPos && <span style={{ color: '#888', fontSize: 11, marginLeft: 8 }}>
              {sellingPos.amount_g}g @ ¥{sellingPos.open_price.toFixed(2)}
            </span>}
          </span>
        }
        open={sellOpen}
        onOk={handleSell}
        onCancel={() => { setSellOpen(false); sellForm.resetFields(); setSellingPos(null) }}
        confirmLoading={loading}
        okText="确认卖出"
        okButtonProps={{ danger: true }}
        cancelText="取消"
        styles={modalStyle}
      >
        <Form form={sellForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>卖出价格 (元/g)</span>} name="close_price" rules={[{ required: true }, { type: 'number', min: 0.01 }]}>
            <InputNumber style={inputStyle} min={0.01} step={0.01} precision={2} prefix="¥" />
          </Form.Item>
          <Form.Item label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>卖出时间</span>} name="close_date" rules={[{ required: true }]}>
            <DatePicker showTime style={inputStyle} format="YYYY-MM-DD HH:mm" />
          </Form.Item>
          {sellingPos && price > 0 && (() => {
            const cp = sellForm.getFieldValue('close_price') || price
            const pnl = (cp - sellingPos.open_price) * sellingPos.amount_g - cp * sellingPos.amount_g * SELL_FEE
            const color = pnl >= 0 ? '#00ff88' : '#ff4d4f'
            return (
              <div style={{ padding: '8px 12px', background: '#060b14', border: '1px solid #1a3a5c', borderRadius: 4, fontSize: 12 }}>
                <span style={{ color: '#4fc3f7' }}>预计盈亏：</span>
                <span style={{ color, fontFamily: "'Courier New', monospace", marginLeft: 8 }}>
                  {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)} 元
                </span>
              </div>
            )
          })()}
        </Form>
      </Modal>
    </>
  )
}
