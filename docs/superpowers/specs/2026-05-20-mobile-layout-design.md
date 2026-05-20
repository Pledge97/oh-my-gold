# 手机端响应式布局设计

## 目标

当用户在手机端（屏幕宽度 ≤ 768px）访问时，将桌面端的左右分栏布局替换为纵向滚动布局，组件顺序从上至下依次为：顶部状态栏、信号面板、底仓面板、Tick 图、日K图、底部绩效。

---

## 技术方案

**方案：`useIsMobile` hook + 条件内联 style**

- 新增 `src/hooks/useIsMobile.ts`，监听 `window.resize`，返回 `window.innerWidth <= 768` 的布尔值
- `App.tsx` 调用该 hook，根据 `isMobile` 切换布局样式
- 各组件接收 `isMobile?: boolean` prop，手机端时覆盖高度和溢出样式
- 不引入新依赖，与现有内联 style 风格一致

---

## 布局规格

### 桌面端（> 768px，保持不变）

```
100vh flex column, overflow hidden
├── StatusBar（~60px, flexShrink: 0）
├── 主内容区（flex: 1, grid: 1fr 600px）
│   ├── 左列：PriceChart + TickChart（各 flex: 1）
│   └── 右列：SignalPanel + PositionTable（各 flex: 1）
└── PerformanceStats（~80px, flexShrink: 0）
```

### 手机端（≤ 768px，新增）

```
min-height: 100vh, flex column, overflow-y: auto
├── StatusBar（sticky top: 0, z-index: 100）
├── SignalPanel（height: 250px）
├── PositionTable（height: 250px）
├── TickChart（height: 250px）
├── PriceChart（height: 250px）
└── PerformanceStats（自然高度）
```

组件间 gap: 8px，整体 padding: 8px。

---

## 组件改动明细

### `src/hooks/useIsMobile.ts`（新建）

- 监听 `window.resize` 事件，返回 `boolean`
- 使用 `useState` + `useEffect`，组件卸载时移除监听器
- 断点：`window.innerWidth <= 768`

### `App.tsx`

- 调用 `useIsMobile()`
- 手机端：根容器改为 `flexDirection: column, overflowY: auto, minHeight: '100vh'`，移除 `overflow: hidden`
- 手机端：移除 grid 容器，改为直接纵向排列各组件
- 手机端：组件顺序：StatusBar → SignalPanel → PositionTable → TickChart → PriceChart → PerformanceStats
- 桌面端：保持现有布局不变
- 将 `isMobile` prop 传递给 StatusBar、SignalPanel、PositionTable、TickChart（PriceChart）、PerformanceStats

### `StatusBar.tsx`

手机端隐藏以下字段（条件渲染，`isMobile` 为 true 时不渲染）：
- 持仓金额
- 累计盈亏
- 右侧市场状态区块中的开市/休市

手机端保留：金价、熔断（条件显示）、持仓克数、持仓均价、持仓盈亏、行情

手机端布局调整：
- `position: sticky, top: 0, zIndex: 100`
- `gap` 从 24 缩小到 12
- 金价字号从 28 缩小到 22

### `SignalPanel.tsx`

- 接收 `isMobile?: boolean` prop
- 手机端：外层容器 `height: 250px, overflow: hidden`，内部表格保持现有滚动逻辑

### `PositionTable.tsx`

- 接收 `isMobile?: boolean` prop
- 手机端：外层容器 `height: 250px, overflow: hidden`，内部表格保持现有滚动逻辑

### `TickChart.tsx`

- 接收 `isMobile?: boolean` prop
- 手机端：容器 `height: 250px`，图表库（lightweight-charts）会自动 resize 适应容器

### `PriceChart.tsx`（日K图）

- 接收 `isMobile?: boolean` prop
- 手机端：容器 `height: 250px`，图表库自动 resize 适应容器

### `PerformanceStats.tsx`

- 接收 `isMobile?: boolean` prop
- 手机端：`StatCard` 容器改为 `flexWrap: wrap`，每张卡片 `minWidth: calc(33% - 8px)`，实现 3列 wrap 布局

---

## 不改动的内容

- 桌面端布局和样式完全不变
- 组件内部数据逻辑、WebSocket、状态管理不变
- 图表库配置不变（resize 由容器尺寸驱动）
- `index.css` 全局样式不变

---

## 验收标准

1. 桌面端（> 768px）布局与现在完全一致
2. 手机端（≤ 768px）组件顺序：状态栏 → 信号面板 → 底仓面板 → Tick图 → 日K图 → 绩效
3. 手机端状态栏吸顶，滚动时不消失
4. 手机端状态栏隐藏：持仓金额、累计盈亏、右侧市场状态区块
5. 手机端各图表/面板高度 250px，内容可在组件内滚动
6. 手机端绩效统计为 3列 wrap 布局
7. 浏览器窗口 resize 时布局实时切换，无需刷新
