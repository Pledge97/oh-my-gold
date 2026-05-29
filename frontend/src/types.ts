export interface Indicators {
  adx: number
  plus_di: number
  minus_di: number
  bb_upper: number
  bb_mid: number
  bb_lower: number
  rsi: number
  atr: number
}

export interface Position {
  id: number
  open_price: number
  amount_g: number
  pnl_pct: number
  pnl_yuan: number
}

/** V3 T仓组合持仓（来自 WebSocket portfolio 字段，由 _portfolio_snapshot 生成） */
export interface PortfolioPosition {
  round_counter: number
  total_amount_g: number
  avg_cost: number
  pnl_pct: number
  pnl_yuan: number
  tp1_done: boolean
  tp2_done: boolean
  next_buy: number | null   // 下次买入触发价
  next_tp: number | null    // 下次止盈触发价
  next_stop: number | null  // 下次止损触发价
}

export interface WsMessage {
  is_market_open: boolean
  ts: number
  price: number
  market_state: string
  indicators: Indicators
  signal: { type: string; amount_g: number; reason: string } | null
  circuit_breaker: { active: boolean; level: number | null }
  /** V3：T仓组合快照，由后端 on_tick_v2 推送 */
  portfolio?: PortfolioPosition
}

export interface Signal {
  id: number | string
  ts: number
  type: string
  mode: string
  price: number | null
  amount_g: number | null
  reason: string
  /** 卖出信号的本次已实现盈亏（元）；买入信号为 null */
  pnl_yuan?: number | null
}

export interface Performance {
  total_trades: number
  total_pnl_yuan: number
  cumulative_pnl_yuan: number
  win_rate: number
  avg_win_yuan: number
  avg_loss_yuan: number
  profit_loss_ratio: number
}

export interface DailyPrice {
  date: string
  open: number
  high: number
  low: number
  close: number
}
