import { useEffect, useState } from 'react'
import { Button, DatePicker, Form, InputNumber, Modal, Table } from 'antd'
import { PlusOutlined, DollarOutlined, DeleteOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useStore, BaseHolding } from '../store/useStore'
import { createBaseHolding, closeBaseHolding, fetchBaseHoldings } from '../api/client'

/** 卖出手续费率（与后端 config.SELL_FEE_RATE 保持一致）。 */
const SELL_FEE_RATE = 0.004

// Table body fills the remaining panel height so the header can stay fixed.
const TABLE_SCROLL_HEIGHT = '100%'

interface BuyFormValues {
  open_price: number
  amount_yuan?: number
  amount_g?: number
  open_date: dayjs.Dayjs
}

interface SellFormValues {
  close_price: number
  close_date: dayjs.Dayjs
}

export function PositionTable() {
  const [buyOpen, setBuyOpen] = useState(false)
  const [sellOpen, setSellOpen] = useState(false)
  const [sellingPos, setSellingPos] = useState<BaseHolding | null>(null)
  const [loading, setLoading] = useState(false)
  const [buyForm] = Form.useForm<BuyFormValues>()
  const [sellForm] = Form.useForm<SellFormValues>()
  const { lastSignalTs, baseHoldings, setBaseHoldings, price } = useStore()

  const reload = () => fetchBaseHoldings('OPEN').then(setBaseHoldings)

  useEffect(() => {
    reload()
  }, [])
  useEffect(() => {
    if (lastSignalTs > 0) reload()
  }, [lastSignalTs])

  const handleBuy = async () => {
    const values = await buyForm.validateFields()
    setLoading(true)
    try {
      await createBaseHolding({
        amount_g: values.amount_g!,
        open_price: values.open_price,
        open_date: values.open_date.format('YYYY-MM-DD')
      })
      buyForm.resetFields()
      setBuyOpen(false)
      reload()
    } finally {
      setLoading(false)
    }
  }

  const openSell = (pos: BaseHolding) => {
    setSellingPos(pos)
    sellForm.setFieldsValue({
      close_price: price || pos.open_price,
      close_date: dayjs()
    })
    setSellOpen(true)
  }

  const handleSell = async () => {
    if (!sellingPos) return
    const values = await sellForm.validateFields()
    setLoading(true)
    try {
      await closeBaseHolding(sellingPos.id, {
        close_price: values.close_price,
        close_date: values.close_date.format('YYYY-MM-DD HH:mm')
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
      title: '买入价',
      dataIndex: 'open_price',
      key: 'open_price',
      render: (v: number) => <span style={{ color: '#f0d060', fontFamily: "'Courier New', monospace", fontSize: 12 }}>{v.toFixed(2)}</span>
    },
    {
      title: '克数',
      dataIndex: 'amount_g',
      key: 'amount_g',
      render: (v: number) => <span style={{ color: '#c8d8e8', fontSize: 11 }}>{v}g</span>
    },
    {
      title: '浮盈',
      key: 'pnl',
      width: 150,
      render: (_: unknown, row: BaseHolding) => {
        if (!price || price === 0) return <span style={{ color: '#2a4a6a' }}>—</span>
        const pnl = (price - row.open_price) * row.amount_g - price * row.amount_g * SELL_FEE_RATE
        const pct = pnl / (row.open_price * row.amount_g)
        const color = pnl >= 0 ? '#ff4d4f' : '#00ff88'
        return (
          <span style={{ color, fontFamily: "'Courier New', monospace", fontSize: 12, textShadow: `0 0 6px ${color}44` }}>
            {pnl >= 0 ? '+' : ''}
            {pnl.toFixed(2)}
            <span style={{ fontSize: 10, marginLeft: 4, opacity: 0.8 }}>
              ({pct >= 0 ? '+' : ''}
              {(pct * 100).toFixed(2)}%)
            </span>
          </span>
        )
      }
    },
    {
      title: '买入时间',
      dataIndex: 'open_ts',
      key: 'open_ts',
      render: (v: number) => <span style={{ color: '#4fc3f7', fontSize: 11 }}>{new Date(v).toLocaleDateString('zh-CN')}</span>
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, row: BaseHolding) => (
        <div style={{ display: 'flex', gap: 4 }}>
          <Button type="text" size="small" icon={<DollarOutlined />} onClick={() => openSell(row)} style={{ color: '#ff4d4f', padding: 0 }} title="卖出" />
          <Button
            type="text"
            size="small"
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: <span style={{ color: '#4fc3f7' }}>确认删除</span>,
                content: (
                  <span style={{ color: '#aaa' }}>
                    确定要删除这笔底仓吗？（{row.amount_g}g ¥{row.open_price.toFixed(2)}）
                  </span>
                ),
                okText: '删除',
                okType: 'danger',
                cancelText: '取消',
                onOk: async () => {
                  await closeBaseHolding(row.id, {
                    close_price: row.open_price,
                    close_date: dayjs().format('YYYY-MM-DD HH:mm')
                  })
                  reload()
                },
                modalRender: (modal) => <div style={{ background: '#0a1628', border: '1px solid #1a3a5c', borderRadius: 4 }}>{modal}</div>
              })
            }}
            style={{ color: '#ff4d4f', padding: 0 }}
            title="删除"
          />
        </div>
      )
    }
  ]

  const modalStyle = {
    content: { background: '#0a1628', border: '1px solid #1a3a5c' },
    header: { background: '#0a1628', borderBottom: '1px solid #1a3a5c' },
    footer: { background: '#0a1628' },
    mask: { backdropFilter: 'blur(2px)' }
  }

  const inputStyle = { width: '100%', background: '#060b14', borderColor: '#1a3a5c', color: '#c8d8e8' }

  const totalAmountG = baseHoldings.reduce((sum, pos) => sum + pos.amount_g, 0)
  const totalMarketValue = price ? price * totalAmountG : 0
  const totalPnl = price ? baseHoldings.reduce((sum, pos) => sum + (price - pos.open_price) * pos.amount_g - price * pos.amount_g * SELL_FEE_RATE, 0) : 0
  const totalCost = baseHoldings.reduce((sum, pos) => sum + pos.open_price * pos.amount_g, 0)
  const totalPnlPct = totalCost > 0 ? totalPnl / totalCost : 0

  return (
    <>
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
        <div className="panel-title" style={{ display: 'flex', alignItems: 'center' }}>
          底仓
          <Button
            size="small"
            icon={<PlusOutlined />}
            onClick={() => setBuyOpen(true)}
            style={{ background: 'transparent', border: '1px solid #1a3a5c', color: '#4fc3f7', fontSize: 11, height: 22, padding: '0 8px' }}
          >
            手动建仓
          </Button>
          <span style={{ marginLeft: 'auto', display: 'flex', gap: 12, fontSize: 11 }}>
            {baseHoldings.length > 0 ? (
              <>
                <span>
                  <span style={{ color: '#4a6a8a' }}>持仓 </span>
                  <span style={{ color: '#c8d8e8', fontFamily: "'Courier New', monospace" }}>
                    {totalAmountG.toFixed(1)}
                    <span style={{ fontSize: 12, marginLeft: 3, opacity: 0.7, textTransform: 'none' }}>g</span>
                  </span>
                </span>
                <span>
                  <span style={{ color: '#4a6a8a' }}>金额 </span>
                  <span style={{ color: '#f0d060', fontFamily: "'Courier New', monospace" }}>{totalMarketValue.toFixed(0)}</span>
                </span>
                <span style={{ color: totalPnl >= 0 ? '#ff4d4f' : '#00ff88', fontFamily: "'Courier New', monospace" }}>
                  <span style={{ color: '#4a6a8a' }}>浮盈 </span>
                  {totalPnl >= 0 ? '+' : ''}
                  {totalPnl.toFixed(2)}
                  <span style={{ fontSize: 10, marginLeft: 3, opacity: 0.85 }}>
                    ({totalPnlPct >= 0 ? '+' : ''}
                    {(totalPnlPct * 100).toFixed(2)}%)
                  </span>
                </span>
              </>
            ) : (
              <span style={{ color: '#2a4a6a', fontSize: 10 }}>暂无底仓</span>
            )}
          </span>
        </div>
        <div className="panel-table-body">
          <Table<BaseHolding>
            dataSource={baseHoldings}
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


      {/* 建仓弹窗 */}
      <Modal
        title={<span style={{ color: '#4fc3f7', letterSpacing: '0.08em', fontSize: 13 }}>手动建仓</span>}
        open={buyOpen}
        onOk={handleBuy}
        onCancel={() => {
          setBuyOpen(false)
          buyForm.resetFields()
        }}
        confirmLoading={loading}
        okText="确认建仓"
        cancelText="取消"
        styles={modalStyle}
      >
        <Form
          form={buyForm}
          layout="vertical"
          initialValues={{ open_date: dayjs() }}
          style={{ marginTop: 16 }}
          onValuesChange={(changed, all) => {
            const { open_price, amount_yuan, amount_g } = all
            if (!open_price || open_price <= 0) return

            if (changed.amount_yuan !== undefined && amount_yuan && amount_yuan > 0) {
              buyForm.setFieldsValue({ amount_g: amount_yuan / open_price })
            } else if (changed.amount_g !== undefined && amount_g && amount_g > 0) {
              buyForm.setFieldsValue({ amount_yuan: amount_g * open_price })
            } else if (changed.open_price !== undefined) {
              if (amount_yuan && amount_yuan > 0) {
                buyForm.setFieldsValue({ amount_g: amount_yuan / open_price })
              } else if (amount_g && amount_g > 0) {
                buyForm.setFieldsValue({ amount_yuan: amount_g * open_price })
              }
            }
          }}
        >
          <Form.Item
            label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入价格 (元/g)</span>}
            name="open_price"
            rules={[{ required: true, message: '请输入买入价格' }, { type: 'number', min: 0.01 }]}
          >
            <InputNumber style={inputStyle} min={0.01} step={0.01} precision={2} prefix="¥" />
          </Form.Item>
          <Form.Item
            label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入金额 (元)</span>}
            name="amount_yuan"
            rules={[
              { required: true, message: '请输入买入金额' },
              { type: 'number', min: 0.01, message: '买入金额不能小于0.01' }
            ]}
          >
            <InputNumber style={inputStyle} min={0.01} step={1} precision={2} prefix="¥" />
          </Form.Item>
          <Form.Item
            label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>买入克数 (g)</span>}
            name="amount_g"
            rules={[
              { required: true, message: '请输入买入克数' },
              { type: 'number', min: 0.01, message: '买入克数不能小于0.01' }
            ]}
          >
            <InputNumber style={inputStyle} min={0.01} step={1} precision={2} suffix="g" />
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
            {sellingPos && (
              <span style={{ color: '#888', fontSize: 11, marginLeft: 8 }}>
                {sellingPos.amount_g}g @ ¥{sellingPos.open_price.toFixed(2)}
              </span>
            )}
          </span>
        }
        open={sellOpen}
        onOk={handleSell}
        onCancel={() => {
          setSellOpen(false)
          sellForm.resetFields()
          setSellingPos(null)
        }}
        confirmLoading={loading}
        okText="确认卖出"
        okButtonProps={{ danger: true }}
        cancelText="取消"
        styles={modalStyle}
      >
        <Form form={sellForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>卖出价格 (元/g)</span>}
            name="close_price"
            rules={[{ required: true }, { type: 'number', min: 0.01 }]}
          >
            <InputNumber style={inputStyle} min={0.01} step={0.01} precision={2} prefix="¥" />
          </Form.Item>
          <Form.Item label={<span style={{ color: '#4fc3f7', fontSize: 12 }}>卖出时间</span>} name="close_date" rules={[{ required: true }]}>
            <DatePicker showTime style={inputStyle} format="YYYY-MM-DD HH:mm" />
          </Form.Item>
          {sellingPos &&
            price > 0 &&
            (() => {
              const cp = sellForm.getFieldValue('close_price') || price
              const pnl = (cp - sellingPos.open_price) * sellingPos.amount_g - cp * sellingPos.amount_g * SELL_FEE_RATE
              const color = pnl >= 0 ? '#ff4d4f' : '#00ff88'
              return (
                <div style={{ padding: '8px 12px', background: '#060b14', border: '1px solid #1a3a5c', borderRadius: 4, fontSize: 12 }}>
                  <span style={{ color: '#4fc3f7' }}>预计盈亏：</span>
                  <span style={{ color, fontFamily: "'Courier New', monospace", marginLeft: 8 }}>
                    {pnl >= 0 ? '+' : ''}
                    {pnl.toFixed(2)} 元
                  </span>
                </div>
              )
            })()}
        </Form>
      </Modal>
    </>
  )
}
