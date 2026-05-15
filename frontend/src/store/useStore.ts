import { create } from 'zustand'
import type { WsMessage, Signal, Performance, DailyPrice } from '../types'

interface Store {
  price: number
  marketState: string
  indicators: WsMessage['indicators'] | null
  positions: WsMessage['positions']
  cbActive: boolean
  cbLevel: number | null
  signals: Signal[]
  performance: Performance | null
  dailyPrices: DailyPrice[]
  setWsMessage: (msg: WsMessage) => void
  setSignals: (s: Signal[]) => void
  setPerformance: (p: Performance) => void
  setDailyPrices: (d: DailyPrice[]) => void
}

export const useStore = create<Store>((set) => ({
  price: 0,
  marketState: 'OSCILLATION',
  indicators: null,
  positions: [],
  cbActive: false,
  cbLevel: null,
  signals: [],
  performance: null,
  dailyPrices: [],
  setWsMessage: (msg) => set({
    price: msg.price,
    marketState: msg.market_state,
    indicators: msg.indicators,
    positions: msg.positions,
    cbActive: msg.circuit_breaker.active,
    cbLevel: msg.circuit_breaker.level,
  }),
  setSignals: (signals) => set({ signals }),
  setPerformance: (performance) => set({ performance }),
  setDailyPrices: (dailyPrices) => set({ dailyPrices }),
}))
