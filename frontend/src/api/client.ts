const BASE = '/api'
// 日 K 默认展示最近半年的数据。
const DEFAULT_DAILY_MONTHS = 6

/**
 * 按本地日期格式化接口查询参数。
 *
 * @param date 需要格式化的日期。
 * @returns YYYY-MM-DD 日期字符串。
 */
const formatDateParam = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * 计算日 K 默认查询时间范围。
 *
 * @returns 近半年的开始日期和结束日期。
 */
const getDefaultDailyRange = () => {
  const endDate = new Date()
  const startDate = new Date(endDate)
  startDate.setMonth(startDate.getMonth() - DEFAULT_DAILY_MONTHS)
  return {
    startDate: formatDateParam(startDate),
    endDate: formatDateParam(endDate),
  }
}

export const fetchSignals = (limit = 50) =>
  fetch(`${BASE}/signals?limit=${limit}`).then(r => r.json())

/** @deprecated V3 起底仓迁移至 fetchBaseHoldings，此函数仅供旧路由兼容保留 */
export const fetchPositions = (status = 'OPEN', source = 'all') =>
  fetch(`${BASE}/positions?status=${status}&source=${source}`).then(r => r.json())

export const fetchPerformance = () =>
  fetch(`${BASE}/performance`).then(r => r.json())

export const fetchDailyPrices = (range = getDefaultDailyRange()) => {
  const query = new URLSearchParams({
    start_date: range.startDate,
    end_date: range.endDate,
  })
  return fetch(`${BASE}/prices/daily?${query.toString()}`).then(r => r.json())
}

export const fetchLatestPrice = () =>
  fetch(`${BASE}/prices/latest`).then(r => r.json()) as Promise<{ price: number }>

export const fetchTickPrices = (hours = 24) =>
  fetch(`${BASE}/prices/tick?hours=${hours}`).then(r => r.json())

export const resumeCircuitBreaker = () =>
  fetch(`${BASE}/circuit-breaker/resume`, { method: 'POST' }).then(r => r.json())

/** @deprecated V3 起请改用 createBaseHolding */
export const createPosition = (body: { amount_g: number; open_price: number; open_date: string }) =>
  fetch(`${BASE}/positions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json())

/** @deprecated V3 起请改用 closeBaseHolding */
export const closePosition = (posId: number, body: { close_price: number; close_date: string }) =>
  fetch(`${BASE}/positions/${posId}/close`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json())

// ── V3 底仓 API ────────────────────────────────────────────────

/**
 * 查询底仓列表。
 *
 * @param status 持仓状态，默认 'OPEN'。
 */
export const fetchBaseHoldings = (status = 'OPEN') =>
  fetch(`${BASE}/base_holdings?status=${status}`).then(r => r.json())

/**
 * 新建底仓记录。
 *
 * @param body 建仓参数：克数、买入价、买入日期（YYYY-MM-DD）。
 */
export const createBaseHolding = (body: { amount_g: number; open_price: number; open_date: string }) =>
  fetch(`${BASE}/base_holdings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json())

/**
 * 平仓底仓记录。
 *
 * @param posId 底仓 ID。
 * @param body  平仓参数：平仓价、平仓时间（YYYY-MM-DD HH:mm）。
 */
export const closeBaseHolding = (posId: number, body: { close_price: number; close_date: string }) =>
  fetch(`${BASE}/base_holdings/${posId}/close`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json())

