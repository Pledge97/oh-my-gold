# 手机端响应式布局 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 当屏幕宽度 ≤ 768px 时，将桌面端左右分栏布局替换为纵向滚动布局，组件顺序：状态栏 → 信号面板 → 底仓面板 → Tick图 → 日K图 → 绩效。

**Architecture:** 新增 `useIsMobile` hook 监听 window resize，`App.tsx` 根据返回值切换布局，各组件接收 `isMobile` prop 覆盖高度和可见性。桌面端布局完全不变。

**Tech Stack:** React 18, TypeScript, 内联 style（无 Tailwind/CSS Modules），Ant Design 5.x

---

## File Map

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/hooks/useIsMobile.ts` | 新建 | 监听 resize，返回 `window.innerWidth <= 768` |
| `frontend/src/App.tsx` | 修改 | 调用 hook，切换根容器和内容区布局 |
| `frontend/src/components/StatusBar.tsx` | 修改 | 接收 `isMobile`，手机端隐藏字段 + sticky |
| `frontend/src/components/SignalPanel.tsx` | 修改 | 接收 `isMobile`，手机端固定 250px 高度 |
| `frontend/src/components/PositionTable.tsx` | 修改 | 接收 `isMobile`，手机端固定 250px 高度 |
| `frontend/src/components/TickChart.tsx` | 修改 | 接收 `isMobile`，手机端固定 250px 高度 |
| `frontend/src/components/PriceChart.tsx` | 修改 | 接收 `isMobile`，手机端固定 250px 高度 |
| `frontend/src/components/PerformanceStats.tsx` | 修改 | 接收 `isMobile`，手机端 3列 wrap 布局 |

---

## Task 1: 新建 `useIsMobile` hook

**Files:**
- Create: `frontend/src/hooks/useIsMobile.ts`

- [ ] **Step 1: 创建文件**

```typescript
import { useState, useEffect } from 'react'

/** 屏幕宽度断点，≤ 此值时视为手机端。 */
const MOBILE_BREAKPOINT = 768

/**
 * 监听窗口宽度，返回当前是否为手机端。
 *
 * @returns 当 window.innerWidth ≤ 768 时为 true。
 */
export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth <= MOBILE_BREAKPOINT)

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  return isMobile
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无报错输出

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useIsMobile.ts
git commit -m "feat: add useIsMobile hook"
```

---

## Task 2: 修改 `App.tsx` 切换布局

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 修改 App.tsx**

将文件替换为以下内容（逻辑部分不变，仅 JSX 部分改动）：

```tsx
import { useEffect, useRef } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { useStore } from './store/useStore'
import { useIsMobile } from './hooks/useIsMobile'
import { fetchSignals, fetchPerformance, fetchDailyPrices } from './api/client'
import { StatusBar } from './components/StatusBar'
import { PriceChart } from './components/PriceChart'
import { TickChart } from './components/TickChart'
import { SignalPanel } from './components/SignalPanel'
import { PerformanceStats } from './components/PerformanceStats'
import { PositionTable } from './components/PositionTable'

export default function App() {
  useWebSocket()
  const { setSignals, setPerformance, setDailyPrices, isMarketOpen, price } = useStore()
  const isMobile = useIsMobile()
  // 记录已处理的最新信号 id，避免无新信号时重复刷新绩效统计。
  const latestSignalIdRef = useRef<number | null>(null)

  useEffect(() => {
    document.title = Number.isFinite(price) && price > 0
      ? `¥${price.toFixed(2)} | Gold Inspector`
      : 'Gold Inspector'
  }, [price])

  useEffect(() => {
    fetchSignals().then((signals) => {
      latestSignalIdRef.current = signals[0]?.id ?? null
      setSignals(signals)
    })
    fetchPerformance().then(setPerformance)
    fetchDailyPrices().then(setDailyPrices)
  }, [])

  useEffect(() => {
    if (!isMarketOpen) return
    const interval = setInterval(() => {
      fetchSignals().then((signals) => {
        const latestSignalId = signals[0]?.id ?? null
        setSignals(signals)
        if (latestSignalId !== latestSignalIdRef.current) {
          latestSignalIdRef.current = latestSignalId
          fetchPerformance().then(setPerformance)
        }
      })
    }, 30000)
    return () => clearInterval(interval)
  }, [isMarketOpen, setSignals, setPerformance])

  if (isMobile) {
    return (
      <div style={{ minHeight: '100vh', background: '#060b14', display: 'flex', flexDirection: 'column' }}>
        <div className="dashboard-scanline" />
        <StatusBar isMobile />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 8 }}>
          <SignalPanel isMobile />
          <PositionTable isMobile />
          <TickChart isMobile />
          <PriceChart isMobile />
          <PerformanceStats isMobile />
        </div>
      </div>
    )
  }

  return (
    <div style={{ height: '100vh', background: '#060b14', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 扫描线 */}
      <div className="dashboard-scanline" />

      {/* 顶部状态栏 */}
      <StatusBar />

      {/* 主内容 */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* 中间区域：图表 + 右侧面板 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 600px', gap: 12, flex: 1, minHeight: 0, overflow: 'hidden' }}>
          {/* K线图 + Tick图 */}
          <div style={{
            overflow: 'hidden',
            display: 'flex',
            gap: 12,
            flexDirection: 'column',
            minHeight: 0,
          }}>
            <PriceChart />
            <TickChart />
          </div>

          {/* 右侧：信号面板上半，底仓下半 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0 }}>
            <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <SignalPanel />
            </div>
            <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <PositionTable />
            </div>
          </div>
        </div>

        {/* 底部绩效 */}
        <PerformanceStats />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 报错提示各组件不接受 `isMobile` prop（这是预期的，后续 Task 会修复）

- [ ] **Step 3: Commit（暂时带类型错误）**

```bash
git add frontend/src/App.tsx
git commit -m "feat: wire isMobile into App layout"
```

---

## Task 3: 修改 `StatusBar.tsx`

**Files:**
- Modify: `frontend/src/components/StatusBar.tsx`

手机端：隐藏持仓金额、累计盈亏、开市/休市；保留行情；sticky 吸顶；金价字号缩小；gap 缩小。

- [ ] **Step 1: 修改组件签名，添加 isMobile prop**

在 `StatusBar.tsx` 的 `export function StatusBar()` 改为：

```tsx
export function StatusBar({ isMobile = false }: { isMobile?: boolean }) {
```

- [ ] **Step 2: 修改根容器 style，手机端添加 sticky**

将根容器 `<div style={{ padding: '10px 20px', ... }}>` 的 style 改为：

```tsx
style={{
  padding: '10px 20px',
  background: 'linear-gradient(90deg, #060b14 0%, #0a1628 50%, #060b14 100%)',
  borderBottom: '1px solid #1a3a5c',
  display: 'flex',
  alignItems: 'center',
  gap: isMobile ? 12 : 24,
  position: isMobile ? 'sticky' : 'relative',
  top: isMobile ? 0 : undefined,
  zIndex: isMobile ? 100 : undefined,
  overflow: 'hidden',
  flexShrink: 0,
  background: 'linear-gradient(90deg, #060b14 0%, #0a1628 50%, #060b14 100%)',
}}
```

注意：上面有两个 `background` key，删掉第一个，保留最后一个。正确写法：

```tsx
style={{
  padding: '10px 20px',
  background: 'linear-gradient(90deg, #060b14 0%, #0a1628 50%, #060b14 100%)',
  borderBottom: '1px solid #1a3a5c',
  display: 'flex',
  alignItems: 'center',
  gap: isMobile ? 12 : 24,
  position: isMobile ? 'sticky' : 'relative',
  top: isMobile ? 0 : undefined,
  zIndex: isMobile ? 100 : undefined,
  overflow: 'hidden',
  flexShrink: 0,
}}
```

- [ ] **Step 3: 手机端金价字号缩小**

将金价 `Typography.Text` 的 `fontSize: 28` 改为：

```tsx
fontSize: isMobile ? 22 : 28,
```

- [ ] **Step 4: 手机端隐藏持仓金额**

找到"持仓金额"区块（包含前面的分隔线），用条件渲染包裹：

```tsx
{!isMobile && (
  <>
    <div style={{ width: 1, height: 36, background: '#1a3a5c' }} />
    {/* 持仓金额 */}
    <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.4 }}>
      <span style={{ fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em', textTransform: 'uppercase' }}>持仓金额</span>
      <span style={{ fontSize: 16, fontWeight: 700, color: '#f0d060', fontFamily: "'Courier New', monospace" }}>
        {totalMarketValue.toFixed(0)}
        <span style={{ fontSize: 12, marginLeft: 3, opacity: 0.7 }}>元</span>
      </span>
    </div>
  </>
)}
```

- [ ] **Step 5: 手机端隐藏累计盈亏**

找到"累计盈亏"区块（`{performance && (() => { ... })()}`），用条件渲染包裹：

```tsx
{!isMobile && performance &&
  (() => {
    const cum = performance.cumulative_pnl_yuan
    const cumColor = cum >= 0 ? '#ff4d4f' : '#00ff88'
    return (
      <>
        <div style={{ width: 1, height: 36, background: '#1a3a5c' }} />
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.4 }}>
          <span style={{ fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em', textTransform: 'uppercase' }}>累计盈亏</span>
          <span style={{ fontSize: 16, fontWeight: 700, color: cumColor, textShadow: `0 0 8px ${cumColor}66`, fontFamily: "'Courier New', monospace" }}>
            {cum >= 0 ? '+' : ''}
            {cum.toFixed(2)} 元
          </span>
        </div>
      </>
    )
  })()}
```

注意：原来累计盈亏前没有独立的分隔线，需要把分隔线也移进条件块里。检查原文件第 164 行的分隔线是否在累计盈亏之前，如果是，一并包进 `!isMobile` 条件。

- [ ] **Step 6: 手机端右侧区块隐藏开市/休市，保留行情**

找到右侧区块（`marginLeft: 'auto'` 的 div），将其改为：

```tsx
<div style={{ marginLeft: 'auto', textAlign: 'right', display: 'flex', alignItems: 'center', gap: 16 }}>
  {/* 行情 */}
  <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.4, textAlign: 'right' }}>
    <span style={{ fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em', textTransform: 'uppercase' }}>行情</span>
    <span
      style={{
        fontSize: 13,
        fontWeight: 600,
        color: stateColor,
        textShadow: `0 0 8px ${stateColor}66`,
        letterSpacing: '0.05em'
      }}
    >
      {STATE_LABEL[marketState] ?? marketState}
    </span>
  </div>
  {!isMobile && (
    <>
      <div style={{ width: 1, height: 36, background: '#1a3a5c' }} />
      {/* 市场状态（开市/休市） */}
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.4, textAlign: 'right' }}>
        <span style={{ fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em', textTransform: 'uppercase' }}>市场状态</span>
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: stateColor,
            textShadow: `0 0 8px ${stateColor}66`,
            letterSpacing: '0.05em'
          }}
        >
          {isMarketOpen ? '开市' : '休市'}
        </span>
      </div>
    </>
  )}
</div>
```

- [ ] **Step 7: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit
```

Expected: StatusBar 相关报错消失

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/StatusBar.tsx
git commit -m "feat: StatusBar mobile support"
```

---

## Task 4: 修改 `SignalPanel.tsx`

**Files:**
- Modify: `frontend/src/components/SignalPanel.tsx`

- [ ] **Step 1: 添加 isMobile prop，手机端固定高度**

将 `export function SignalPanel()` 改为：

```tsx
export function SignalPanel({ isMobile = false }: { isMobile?: boolean }) {
```

将根容器 `<div style={{ background: '#0a1628', border: '1px solid #1a3a5c', ... }}>` 的 style 改为：

```tsx
style={{
  background: '#0a1628',
  border: '1px solid #1a3a5c',
  borderRadius: 4,
  overflow: 'hidden',
  ...(isMobile
    ? { height: 250, display: 'flex', flexDirection: 'column' }
    : { flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }
  ),
}}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit
```

Expected: SignalPanel 相关报错消失

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SignalPanel.tsx
git commit -m "feat: SignalPanel mobile support"
```

---

## Task 5: 修改 `PositionTable.tsx`

**Files:**
- Modify: `frontend/src/components/PositionTable.tsx`

- [ ] **Step 1: 添加 isMobile prop，手机端固定高度**

将 `export function PositionTable()` 改为：

```tsx
export function PositionTable({ isMobile = false }: { isMobile?: boolean }) {
```

将内层 `<div style={{ background: '#0a1628', border: '1px solid #1a3a5c', ... }}>` 的 style 改为：

```tsx
style={{
  background: '#0a1628',
  border: '1px solid #1a3a5c',
  borderRadius: 4,
  overflow: 'hidden',
  ...(isMobile
    ? { height: 250, display: 'flex', flexDirection: 'column' }
    : { flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }
  ),
}}
```

注意：`PositionTable` 的根元素是 `<>` Fragment，内层第一个 div 才是面板容器（`background: '#0a1628'` 那个）。

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit
```

Expected: PositionTable 相关报错消失

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PositionTable.tsx
git commit -m "feat: PositionTable mobile support"
```

---

## Task 6: 修改 `TickChart.tsx`

**Files:**
- Modify: `frontend/src/components/TickChart.tsx`

- [ ] **Step 1: 添加 isMobile prop，手机端固定高度**

将 `export function TickChart()` 改为：

```tsx
export function TickChart({ isMobile = false }: { isMobile?: boolean }) {
```

将根容器 `<div style={{ borderTop: '1px solid #1a3a5c', flex: 1, minHeight: 0, ... }}>` 的 style 改为：

```tsx
style={{
  border: '1px solid #1a3a5c',
  borderRadius: 4,
  display: 'flex',
  flexDirection: 'column',
  ...(isMobile
    ? { height: 250 }
    : { flex: 1, minHeight: 0 }
  ),
}}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit
```

Expected: TickChart 相关报错消失

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/TickChart.tsx
git commit -m "feat: TickChart mobile support"
```

---

## Task 7: 修改 `PriceChart.tsx`

**Files:**
- Modify: `frontend/src/components/PriceChart.tsx`

- [ ] **Step 1: 添加 isMobile prop，手机端固定高度**

将 `export function PriceChart()` 改为：

```tsx
export function PriceChart({ isMobile = false }: { isMobile?: boolean }) {
```

将根容器 `<div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', border: '1px solid #1a3a5c', borderRadius: 4 }}>` 的 style 改为：

```tsx
style={{
  display: 'flex',
  flexDirection: 'column',
  border: '1px solid #1a3a5c',
  borderRadius: 4,
  ...(isMobile
    ? { height: 250 }
    : { flex: 1, minHeight: 0 }
  ),
}}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit
```

Expected: PriceChart 相关报错消失

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PriceChart.tsx
git commit -m "feat: PriceChart mobile support"
```

---

## Task 8: 修改 `PerformanceStats.tsx`

**Files:**
- Modify: `frontend/src/components/PerformanceStats.tsx`

- [ ] **Step 1: 添加 isMobile prop，手机端 3列 wrap 布局**

将 `export function PerformanceStats()` 改为：

```tsx
export function PerformanceStats({ isMobile = false }: { isMobile?: boolean }) {
```

将卡片容器 `<div style={{ display: 'flex', gap: 8, padding: 10 }}>` 的 style 改为：

```tsx
style={{
  display: 'flex',
  gap: 8,
  padding: 10,
  ...(isMobile && { flexWrap: 'wrap' }),
}}
```

将 `StatCard` 组件的根 div style 中的 `flex: 1` 改为：

```tsx
flex: isMobile ? '0 0 calc(33.333% - 6px)' : 1,
```

但 `StatCard` 是内部组件，需要给它传 `isMobile`。修改 `StatCardProps` 和 `StatCard`：

```tsx
interface StatCardProps {
  /** 统计项标签。 */
  label: string
  /** 统计项数值文本。 */
  value: string
  /** 数值颜色，默认 #c8d8e8。 */
  color?: string
  /** 数值单位。 */
  unit?: string
  /** 是否手机端布局。 */
  isMobile?: boolean
}

function StatCard({ label, value, color = '#c8d8e8', unit, isMobile = false }: StatCardProps) {
  return (
    <div style={{
      background: '#0a1628',
      border: '1px solid #1a3a5c',
      borderRadius: 4,
      padding: '10px 14px',
      flex: isMobile ? '0 0 calc(33.333% - 6px)' : 1,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* 顶部装饰线 */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, transparent, ${color}66, transparent)`,
      }} />
      <div style={{
        fontSize: 10, color: '#4fc3f7', letterSpacing: '0.1em',
        textTransform: 'uppercase', marginBottom: 6,
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 20, fontWeight: 700, color,
        fontFamily: "'Courier New', monospace",
        textShadow: `0 0 10px ${color}44`,
        lineHeight: 1,
      }}>
        {value}
        {unit && <span style={{ fontSize: 11, color: '#4a6a8a', marginLeft: 3 }}>{unit}</span>}
      </div>
    </div>
  )
}
```

然后在 `PerformanceStats` 的 JSX 中，给每个 `<StatCard>` 传入 `isMobile={isMobile}`：

```tsx
<StatCard label="总交易" value={String(perf.total_trades)} color="#00d4ff" unit="笔" isMobile={isMobile} />
<StatCard
  label="T仓盈亏"
  value={(perf.total_pnl_yuan >= 0 ? '+' : '') + perf.total_pnl_yuan.toFixed(2)}
  color={pnlColor}
  unit="元"
  isMobile={isMobile}
/>
<StatCard label="胜率" value={(perf.win_rate * 100).toFixed(1)} color="#f0a500" unit="%" isMobile={isMobile} />
<StatCard label="平均盈利" value={'+' + perf.avg_win_yuan.toFixed(2)} color="#ff4d4f" unit="元" isMobile={isMobile} />
<StatCard label="平均亏损" value={perf.avg_loss_yuan.toFixed(2)} color="#00ff88" unit="元" isMobile={isMobile} />
<StatCard label="盈亏比" value={perf.profit_loss_ratio.toFixed(2)} color="#00d4ff" isMobile={isMobile} />
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无报错

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PerformanceStats.tsx
git commit -m "feat: PerformanceStats mobile support"
```

---

## Task 9: 最终验证

- [ ] **Step 1: 完整 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无报错

- [ ] **Step 2: 构建验证**

```bash
cd frontend && npm run build
```

Expected: 构建成功，无错误

- [ ] **Step 3: 手动验证桌面端**

启动开发服务器：

```bash
cd frontend && npm run dev
```

在浏览器打开，窗口宽度 > 768px，确认：
- 布局与改动前完全一致（左右分栏，右侧 600px）
- 状态栏显示所有字段（持仓金额、累计盈亏、行情、开市/休市）

- [ ] **Step 4: 手动验证手机端**

浏览器开发者工具切换到手机模拟（375px 宽），确认：
- 组件顺序：状态栏 → 信号面板 → 底仓面板 → Tick图 → 日K图 → 绩效
- 状态栏吸顶（滚动时不消失）
- 状态栏隐藏：持仓金额、累计盈亏、开市/休市；保留：金价、持仓克数、持仓均价、持仓盈亏、行情
- 各面板/图表高度 250px
- 绩效统计为 3列 wrap 布局
- 整页可上下滚动

- [ ] **Step 5: 验证 resize 切换**

拖动浏览器窗口宽度跨越 768px，确认布局实时切换，无需刷新

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: mobile responsive layout"
```
