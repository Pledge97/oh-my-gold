import { create } from 'zustand'
import type { WsMessage, Signal, Performance, DailyPrice, PortfolioPosition } from '../types'

/** V3 底仓记录，对应后端 base_holdings 表。 */
export interface BaseHolding {
  id: number
  open_ts: number
  open_price: number
  amount_g: number
  status: string
  close_ts?: number | null
  close_price?: number | null
  pnl_yuan: number | null
}

interface Store {
  price: number
  marketState: string
  indicators: WsMessage['indicators'] | null
  cbActive: boolean
  cbLevel: number | null
  signals: Signal[]
  performance: Performance | null
  dailyPrices: DailyPrice[]
  lastSignalTs: number
  /** V3 底仓列表，来自 /api/base_holdings */
  baseHoldings: BaseHolding[]
  /** V3 T仓组合快照，来自 WsMessage.portfolio */
  portfolio: PortfolioPosition | null
  isMarketOpen: boolean
  setWsMessage: (msg: WsMessage) => void
  setPrice: (price: number) => void
  setSignals: (s: Signal[]) => void
  setPerformance: (p: Performance) => void
  setDailyPrices: (d: DailyPrice[]) => void
  setBaseHoldings: (p: BaseHolding[]) => void
}

export const useStore = create<Store>((set) => ({
  price: 0,
  marketState: 'OSCILLATION',
  indicators: null,
  cbActive: false,
  cbLevel: null,
  signals: [],
  performance: null,
  dailyPrices: [],
  lastSignalTs: 0,
  baseHoldings: [],
  portfolio: null,
  isMarketOpen: true,
  setWsMessage: (msg) => set((state) => {
    if (msg.is_market_open === false) {
      return { isMarketOpen: false }
    }
    return {
      isMarketOpen: true,
      price: msg.price,
      marketState: msg.market_state,
      indicators: msg.indicators,
      cbActive: msg.circuit_breaker.active,
      cbLevel: msg.circuit_breaker.level,
      lastSignalTs: msg.signal ? msg.ts : state.lastSignalTs,
      portfolio: msg.portfolio ?? state.portfolio,
    }
  }),
  setSignals: (signals) => set({ signals }),
  setPrice: (price) => set({ price }),
  setPerformance: (performance) => set({ performance }),
  setDailyPrices: (dailyPrices) => set({ dailyPrices }),
  setBaseHoldings: (baseHoldings) => set({ baseHoldings }),
}))

