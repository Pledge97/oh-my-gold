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

export interface WsMessage {
  ts: number
  price: number
  market_state: string
  indicators: Indicators
  signal: { type: string; amount_g: number; reason: string } | null
  circuit_breaker: { active: boolean; level: number | null }
  positions: Position[]
}

export interface Signal {
  id: number
  ts: number
  type: string
  mode: string
  price: number
  amount_g: number
  reason: string
}

export interface Performance {
  total_trades: number
  total_pnl_yuan: number
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
