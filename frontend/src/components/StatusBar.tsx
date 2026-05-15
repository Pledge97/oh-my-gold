import { Space, Tag, Typography } from 'antd'
import { useStore } from '../store/useStore'

const STATE_COLOR: Record<string, string> = {
  OSCILLATION: 'blue',
  TREND_UP: 'green',
  TREND_DOWN: 'red',
  TREND_DECAY: 'orange',
}

export function StatusBar() {
  const { price, marketState, cbActive, cbLevel, positions } = useStore()
  const totalPnl = positions.reduce((s, p) => s + p.pnl_yuan, 0)
  return (
    <Space style={{ padding: '8px 16px', background: '#141414', width: '100%' }}>
      <Typography.Text style={{ fontSize: 20, color: '#fff' }}>
        ¥{price.toFixed(2)}/g
      </Typography.Text>
      <Tag color={STATE_COLOR[marketState] ?? 'default'}>{marketState}</Tag>
      {cbActive && <Tag color="red">熔断 L{cbLevel}</Tag>}
      <Typography.Text style={{ color: totalPnl >= 0 ? '#52c41a' : '#ff4d4f' }}>
        持仓盈亏: {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)}元
      </Typography.Text>
    </Space>
  )
}
