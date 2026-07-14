# DreamLoop 前端优化计划（克制版）

## 设计原则

DreamLoop 现有一套自洽的视觉语言：**哑光纸墨质感 + 编辑排版 + 文学/终端混搭**。
变量命名 `--paper` / `--ink`，标题用 Georgia 衬线、标签用 Cascadia 等宽、大量 uppercase eyebrow；
卡片刻意扁平（`box-shadow: none`，hover 只换边框与底色）；已有 1020/760 两档响应式、
`prefers-reduced-motion`、44px 触控目标、focus-visible。**"节制"就是它的高级感来源。**

本计划的目标是**"隐形的精致"（invisible polish）**——强化已有调性，不引入流行套路。
所有改动只涉及 `src/dreamloop/static/style.css`，外加空状态需要少量 HTML。

---

## 明确不做（与另一份计划的分歧）

- **毛玻璃 Glassmorphism** —— 与"哑光纸墨"质感冲突，且 `.topbar` 并非 fixed/sticky（只有 sidebar 是），
  背后无滚动内容穿过，`backdrop-filter` 毫无视觉效果，纯耗 GPU。砍掉。
- **hover `translateY(-2px)` + box-shadow 辉光** —— 直接推翻现有"扁平编辑"决定，会让页面退化成通用 SaaS 仪表盘。砍掉。
- **新增 768 断点的底部固定导航** —— 与现有 1020/760 断点打架，且 iOS 安全区、z-index、body 留白都得处理。
  作为独立改动单独评估（见组件 5），默认不做。

---

## 组件 1 ｜数字排版稳定性（tabular-nums）

统计数字用的是比例衬线体（Georgia），数字宽度不等会导致刷新时轻微跳动。等宽数字修复它，成本近乎为零，完全在调性内。**优先做这条。**

```css
.status-strip strong,
.stat-card strong,
.heat-cell strong,
.spectrum-row strong,
.symbol-row strong,
.insight-callout strong,
.insight-card strong {
  font-variant-numeric: tabular-nums;
}
```

---

## 组件 2 ｜滚动条（主题化，现代 + WebKit 兜底）

低风险、贴主题。用细滚动条、暗紫描边，不要亮色。

```css
:root {
  scrollbar-width: thin;
  scrollbar-color: var(--line-strong) transparent;
}

::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(125, 102, 190, 0.32);
  border: 2px solid transparent;
  background-clip: padding-box;
  border-radius: 999px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(151, 125, 220, 0.5);
  background-clip: padding-box;
}
```

---

## 组件 3 ｜Hover：不加位移辉光，而是"统一 + 平滑"

现有 hover 只改边框/底色，但部分选择器**没有 transition**，状态是硬切的。
真正的精致做法是让这些状态**平滑淡入**，而不是加浮起。这就是这套设计该有的"hover 动画"。

```css
.dream-card,
.recent-row,
.gallery-card,
.heat-cell,
.trend-link {
  transition: border-color 160ms ease, background 160ms ease;
}
```

（`.side-nav a`、`button`、`.primary-cta` 已有 transition，无需改动。）

---

## 组件 4 ｜Loading：克制的"呼吸"而非闪烁脉冲

`.loading-message` 现在只是 `display: block` 直接出现。这是"AI 分析等待"的时刻——
动效要**极轻、慢、低对比**，避免焦虑感。用缓慢的透明度呼吸（2.4s，1 → 0.62），
`prefers-reduced-motion` 已被全局媒体查询接管，无需额外处理。

```css
@keyframes dl-breathe {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.62; }
}

.is-loading .loading-message {
  animation: dl-breathe 2.4s ease-in-out infinite;
}
```

---

## 组件 5 ｜空状态：极淡线描图标，复用 constellation 母题

现在空状态是纯文字，略显未完成。加一个**发丝级线描 SVG**（呼应 `.brand-orbit` 的轨道意象），
描边用 `--amber-dim`/`--line-strong`，尺寸 32–40px，透明度 ~0.5。
**只用在大块空状态**（首次记录、图库空、符号图空），避免每个小提示都塞图标造成杂乱。

CSS：

```css
.empty-state {
  display: grid;
  justify-items: center;
  gap: 12px;
  text-align: center;
  padding: 8px 0;
}

.empty-state-icon {
  width: 40px;
  height: 40px;
  opacity: 0.5;
  stroke: var(--amber-dim);
  fill: none;
  stroke-width: 1;
}
```

HTML（在大块空状态的 `<p class="empty-state">` 前插入内联 SVG，示例——细线新月/轨道）：

```html
<p class="empty-state">
  <svg class="empty-state-icon" viewBox="0 0 40 40" aria-hidden="true">
    <circle cx="20" cy="20" r="13"/>
    <path d="M25 9a13 13 0 1 0 0 22 10 10 0 1 1 0-22z" fill="var(--paper)" stroke="none"/>
    <circle cx="30" cy="12" r="1.2" fill="var(--amber-dim)" stroke="none"/>
  </svg>
  {{ t.first_dream_waiting }}
</p>
```

落点：`index.html` 的 `first_dream_waiting`（121 行）、`gallery_empty`（454 行）、
`symbol_graph_empty`（349 行）。其余小空状态保持纯文字。

---

## 组件 6 ｜细节强化（可选，低风险）

主题化文本选中色，小细节但强化身份认同：

```css
::selection {
  background: rgba(226, 193, 129, 0.28);
  color: var(--text);
}
```

---

## 组件 5b ｜移动端（若确需 app 式底部导航——单独评估，默认不做）

现有响应式已可用（sidebar 在 1020px 折到顶部横排）。**不建议**再加 768 断点。
如果产品确实想要 app 式底部固定导航，按下面的方式做，且作为独立 PR：

- 复用现有 **760px** 断点，不新增第三档，避免规则打架。
- `.sidebar` → `position: fixed; bottom: 0; left: 0; right: 0;`，隐藏 `.brand-mark`/`.side-note`，
  `.side-nav` 横向 `justify-content: space-around`。
- `.app-frame` 底部留白 `padding-bottom: 72px`，并加 `env(safe-area-inset-bottom)` 兼容 iOS 刘海。
- 处理 `z-index` 与滚动穿透；`.side-nav a.active` 的左侧 amber 竖条改为顶部/底部指示。

（除非有明确移动端诉求，这块先搁置。）

---

## 验证计划

桌面端：hover 状态平滑淡入、滚动条配色贴主题、输入不同宽度的数字确认统计数字不跳动、
触发 Analyze 观察 loading 缓慢呼吸、截图检查三处空状态线描图标不俗气。
可访问性：开启 `prefers-reduced-motion` 确认呼吸动画停止；新滚动条/图标对比度可辨。
响应式：在 1020 与 760 两档确认无回归（本计划未新增断点）。
性能：确认所有动画仅用 opacity（无 layout/paint 抖动）。

---

## 一句话总结

只做 **tabular-nums、主题滚动条、hover 平滑过渡、克制呼吸 loading、极淡空状态图标、选中色**
这六项"隐形精致"；**明确砍掉毛玻璃与 hover 浮起辉光**；移动端底部导航当作独立改动另行评估。
