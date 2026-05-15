const BASE = '/api'

export const fetchSignals = (limit = 50) =>
  fetch(`${BASE}/signals?limit=${limit}`).then(r => r.json())

export const fetchPositions = (status = 'OPEN') =>
  fetch(`${BASE}/positions?status=${status}`).then(r => r.json())

export const fetchPerformance = () =>
  fetch(`${BASE}/performance`).then(r => r.json())

export const fetchDailyPrices = (days = 60) =>
  fetch(`${BASE}/prices/daily?days=${days}`).then(r => r.json())

export const fetchTickPrices = (hours = 24) =>
  fetch(`${BASE}/prices/tick?hours=${hours}`).then(r => r.json())

export const resumeCircuitBreaker = () =>
  fetch(`${BASE}/circuit-breaker/resume`, { method: 'POST' }).then(r => r.json())

export const createPosition = (body: { amount_g: number; open_price: number; open_date: string }) =>
  fetch(`${BASE}/positions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json())

export const closePosition = (posId: number, body: { close_price: number; close_date: string }) =>
  fetch(`${BASE}/positions/${posId}/close`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json())
