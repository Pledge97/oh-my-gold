const BASE = '/api'

export const fetchSignals = (limit = 50) =>
  fetch(`${BASE}/signals?limit=${limit}`).then(r => r.json())

export const fetchPositions = (status = 'OPEN') =>
  fetch(`${BASE}/positions?status=${status}`).then(r => r.json())

export const fetchPerformance = () =>
  fetch(`${BASE}/performance`).then(r => r.json())

export const fetchDailyPrices = (days = 60) =>
  fetch(`${BASE}/prices/daily?days=${days}`).then(r => r.json())

export const resumeCircuitBreaker = () =>
  fetch(`${BASE}/circuit-breaker/resume`, { method: 'POST' }).then(r => r.json())
