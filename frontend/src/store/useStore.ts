import { create } from 'zustand'
import type { WsMessage, Signal, Performance, DailyPrice } from '../types'

export interface DbPosition {
  id: number
  open_ts: number
  open_price: number
  amount_g: number
  status: string
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
  dbPositions: DbPosition[]
  setWsMessage: (msg: WsMessage) => void
  setSignals: (s: Signal[]) => void
  setPerformance: (p: Performance) => void
  setDailyPrices: (d: DailyPrice[]) => void
  setDbPositions: (p: DbPosition[]) => void
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
  dbPositions: [],
  setWsMessage: (msg) => set((state) => ({
    price: msg.price,
    marketState: msg.market_state,
    indicators: msg.indicators,
    cbActive: msg.circuit_breaker.active,
    cbLevel: msg.circuit_breaker.level,
    lastSignalTs: msg.signal ? msg.ts : state.lastSignalTs,
  })),
  setSignals: (signals) => set({ signals }),
  setPerformance: (performance) => set({ performance }),
  setDailyPrices: (dailyPrices) => set({ dailyPrices }),
  setDbPositions: (dbPositions) => set({ dbPositions }),
}))
