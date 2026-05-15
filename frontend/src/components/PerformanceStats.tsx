import { Card, Col, Row, Statistic } from 'antd'
import { useStore } from '../store/useStore'

export function PerformanceStats() {
  const perf = useStore(s => s.performance)
  if (!perf) return null
  return (
    <Row gutter={16}>
      <Col span={4}>
        <Card size="small">
          <Statistic title="总交易" value={perf.total_trades} />
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small">
          <Statistic
            title="总盈亏(元)"
            value={perf.total_pnl_yuan}
            precision={2}
            valueStyle={{ color: perf.total_pnl_yuan >= 0 ? '#52c41a' : '#ff4d4f' }}
          />
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small">
          <Statistic title="胜率" value={perf.win_rate * 100} precision={1} suffix="%" />
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small">
          <Statistic title="平均盈利(元)" value={perf.avg_win_yuan} precision={2} />
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small">
          <Statistic title="平均亏损(元)" value={perf.avg_loss_yuan} precision={2} />
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small">
          <Statistic title="盈亏比" value={perf.profit_loss_ratio} precision={2} />
        </Card>
      </Col>
    </Row>
  )
}
