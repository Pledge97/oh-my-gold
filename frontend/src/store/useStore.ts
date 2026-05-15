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
  lastSignalTs: number  // 最近一次有交易信号的时间戳，变化时触发持仓刷新
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
  lastSignalTs: 0,
  setWsMessage: (msg) => set((state) => ({
    price: msg.price,
    marketState: msg.market_state,
    indicators: msg.indicators,
    positions: msg.positions,
    cbActive: msg.circuit_breaker.active,
    cbLevel: msg.circuit_breaker.level,
    lastSignalTs: msg.signal ? msg.ts : state.lastSignalTs,
  })),
  setSignals: (signals) => set({ signals }),
  setPerformance: (performance) => set({ performance }),
  setDailyPrices: (dailyPrices) => set({ dailyPrices }),
}))
