# Hermes Style Guide

Design tokens, component patterns, and conventions used across the Hermes frontend.

> **Scope:** This is a **dark-mode-only** interface.
All opacity-based surfaces (`bg-slate-900/40`, `bg-slate-900/50`, etc.)
assume a `#0f172a` parent background. Do not render this UI in a light container or iframe without a full theme audit.

---

## Table of Contents

1. [Stack](#1-stack)
2. [Color Palette](#2-color-palette)
3. [Accessibility — Color Compliance](#3-accessibility--color-compliance)
4. [Typography](#4-typography)
5. [Spacing & Layout](#5-spacing--layout)
6. [Borders & Surfaces](#6-borders--surfaces)
7. [Components](#7-components)
8. [Charts (Recharts)](#8-charts-recharts)
9. [Scrollbar](#9-scrollbar)
10. [Motion Patterns (Framer Motion)](#10-motion-patterns-framer-motion)
11. [Empty & Loading States](#11-empty--loading-states)
12. [Logo & Brand Rules](#12-logo--brand-rules)
13. [AI Assistance Notes](#13-ai-assistance-notes)
14. [Changelog](#14-changelog)

---

## 1. Stack

| Concern | Tool | Version |
|---|---|---|
| Styling | Tailwind CSS | v3 |
| Component framework | React + TypeScript | 18 |
| Animation | Framer Motion | v10+ |
| Icons | Lucide React | latest |
| Charts | Recharts | v2 |
| Font | Inter (Google Fonts, weights 300–800) | — |

---

## 2. Color Palette

### 2.1 Base / Backgrounds

| Token | Hex | Usage |
|---|---|---|
| `slate-950` | `#0f172a` | App background, header, sidebar |
| `slate-900/40` | `#0f172a66` | Card surface |
| `slate-900/50` | `#0f172a80` | Metric card surface |
| `slate-800` | `#1e293b` | Borders, hover surfaces, chart grid |
| `slate-700` | `#334155` | Input borders, muted borders |

### 2.2 Text

| Token | Hex | Ratio on slate-950 | Usage |
|---|---|---|---|
| `slate-100` | `#f1f5f9` | 16.8:1 AAA | Primary text, page titles |
| `slate-200` | `#e2e8f0` | 13.4:1 AAA | Section/card headings, table data |
| `slate-300` | `#cbd5e1` | 9.8:1 AAA | Form labels, table cell text; **minimum for body text on card surfaces** |
| `slate-400` | `#94a3b8` | 5.9:1 AA | Secondary text, nav inactive, captions, chart axes, placeholders |
| `slate-500` | `#64748b` | 3.1:1 ✗ | **Do not use for readable text.** Decorative/non-text only (borders, dividers). |

> ⚠️ **`slate-500` text is a WCAG AA failure (3.1:1).**
Use `slate-400` as the minimum for any text the user needs to read.
See [Section 3](#3-accessibility--color-compliance) for full details.

### 2.3 Accent / Semantic

| Token | Hex | Ratio on slate-950 | Role | Used for |
|---|---|---|---|---|
| `cyan-400` | `#22d3ee` | 7.4:1 AAA | Primary accent | Download metric, nav active, links |
| `cyan-500` | `#06b6d4` | 4.3:1 AA† | Primary action | Primary button bg, toggle-on (default) |
| `violet-400` | `#a78bfa` | 5.6:1 AA | Upload | Upload metric, Exporters icon |
| `amber-400` | `#fbbf24` | 9.3:1 AAA | Warning / Ping | Ping metric, countdown clock |
| `emerald-400` | `#34d399` | 8.2:1 AAA | Success / Jitter | Jitter metric, success states |
| `orange-400` | `#fb923c` | 5.2:1 AA | Alerts | Alerts section icon, toggle-on (alerts) |
| `red-400` | `#f87171` | 5.1:1 AA | Error | Error banners, failed states |

> † `cyan-500` button text uses `slate-950` as the label color
(4.3:1 — passes AA for large/bold text at the current button spec of
`font-medium` / 14px+). Do not reduce button font size below 14px bold
without switching to `cyan-400` background.

### 2.4 Semantic Color Boundary — Red vs Orange

These two colors appear close in purpose. Their boundaries are explicit:

| Color | Token | Meaning |
| --- | --- | --- |
| Red | `red-400` | **System / test failure** — the speed test itself errored or returned no result |
| Orange | `orange-400` | **User-configured alert notification** — thresholds triggered a user's alert rules |

Never use red for alert notifications or orange for system failures.

### 2.5 Tint Surface System

All colored tint surfaces follow the same pattern: `bg-{color}-500/10 border border-{color}-500/20 text-{color}-400`.
This ensures consistent contrast on the dark parent background.

| Metric / State | Bg tint | Border | Text | Ratio |
|---|---|---|---|---|
| Download / Cyan | `bg-cyan-500/10` | `border-cyan-500/20` | `text-cyan-400` | 7.4:1 AAA |
| Upload / Violet | `bg-violet-500/10` | `border-violet-500/20` | `text-violet-400` | 5.6:1 AA |
| Ping / Amber | `bg-amber-500/10` | `border-amber-500/20` | `text-amber-400` | 9.3:1 AAA |
| Jitter / Emerald | `bg-emerald-500/10` | `border-emerald-500/20` | `text-emerald-400` | 8.2:1 AAA |
| Error | `bg-red-500/10` | `border-red-500/20` | `text-red-400` | 5.1:1 AA |
| Success | `bg-emerald-500/10` | `border-emerald-500/20` | `text-emerald-400` | 8.2:1 AAA |
| Warning | `bg-amber-500/10` | `border-amber-500/20` | `text-amber-400` | 9.3:1 AAA |
| Alert | `bg-orange-500/10` | `border-orange-500/20` | `text-orange-400` | 5.2:1 AA |

### 2.6 Disabled Color Pattern

Disabled colored elements use their normal color at reduced opacity:

```css
/* Disabled toggle, button, or colored indicator */
opacity: 40%;
cursor: not-allowed;

/* Example — disabled cyan toggle */
/* bg-cyan-500/40 instead of bg-cyan-500 */
```

---

## 3. Accessibility — Color Compliance

### 3.1 Summary

| Status | Count | Details |
|---|---|---|
| ✅ Pass AAA (7:1+) | 6 pairs | slate-100/200/300 on slate-950; cyan-400, amber-400, emerald-400 on slate-950 |
| ✅ Pass AA (4.5:1+) | 9 pairs | All accent colors on slate-950; slate-400 on slate-950 |
| ⚠️ Borderline | 2 pairs | cyan-500 button (4.3:1 — AA large text); slate-400 on card surfaces |
| ❌ Fail | 2 pairs | **slate-500 on slate-950 (3.1:1); slate-500 on slate-800 (2.1:1)** |

### 3.2 The 4 Required Token Changes

These are the only changes needed to reach full WCAG AA compliance.
The visual design, all accent colors, all backgrounds, and all component shapes are unchanged.

#### Change 1 — Muted / caption / axis text

**`slate-500` → `slate-400`** everywhere it is used for readable text.

| | Before | After |
|---|---|---|
| Token | `text-slate-500` | `text-slate-400` |
| Hex | `#64748b` | `#94a3b8` |
| Ratio on slate-950 | 3.1:1 ❌ | 5.9:1 ✅ |

Affected locations: helper/caption text, chart axis labels,
empty state sub-text, version badge text, table header labels, placeholder text.

#### Change 2 — Input placeholder text

**`placeholder:text-slate-500` → `placeholder:text-slate-400`** on all inputs and textareas.

| | Before | After |
|---|---|---|
| Token | `placeholder:text-slate-500` | `placeholder:text-slate-400` |
| Ratio on slate-950 | 3.1:1 ❌ | 5.9:1 ✅ |
| Ratio on slate-800 (hover) | 2.1:1 ❌ | 3.6:1 ⚠️→✅ |

Lock this explicitly so it doesn't regress on hover state elevation:

```css
::placeholder {
  color: #94a3b8; /* slate-400 */
}
```

#### Change 3 — Scrollbar thumb

**`#334155` (slate-700) → `#475569` (slate-600)**

Addresses WCAG 1.4.11 Non-text Contrast (3:1 minimum for UI components).

| | Before | After |
|---|---|---|
| Hex | `#334155` (slate-700) | `#475569` (slate-600) |
| Non-text contrast | 1.6:1 ❌ | ~3.4:1 ✅ |

```css
/* Updated scrollbar */
scrollbar-color: #475569 transparent;

::-webkit-scrollbar-thumb {
  background-color: #475569; /* was #334155 */
  border-radius: 9999px;
}
```

#### Change 4 — Body text on semi-transparent card surfaces

On `bg-slate-900/40` card surfaces, use **`slate-300` minimum**
for body-size text. `slate-400` is still acceptable for
secondary/meta text (timestamps, labels) but not for primary descriptions.

| | Before | After |
| --- | --- | --- |
| Card body text | `text-slate-400` (~3.8:1 on card) | `text-slate-300` (~8.4:1 on card) ✅ |
| Card secondary/meta | `text-slate-400` | `text-slate-400` (acceptable for small/secondary) |

### 3.3 What Does Not Change

Every accent color, metric color, semantic tint, background,
border, chart line, and motion pattern is **unchanged**.
The cyberpunk/technical aesthetic is fully preserved.
The 4 changes above affect only secondary neutral text — one step lighter in the slate ramp in each case.

### 3.4 Full Contrast Reference Table

| Foreground | Background | Ratio | AA Normal | AA Large | Used for |
|---|---|---|---|---|---|
| `slate-100` `#f1f5f9` | `slate-950` | 16.8:1 | ✅ AAA | ✅ AAA | Page titles |
| `slate-200` `#e2e8f0` | `slate-950` | 13.4:1 | ✅ AAA | ✅ AAA | Card headings |
| `slate-300` `#cbd5e1` | `slate-950` | 9.8:1 | ✅ AAA | ✅ AAA | Form labels |
| `slate-400` `#94a3b8` | `slate-950` | 5.9:1 | ✅ AA | ✅ AA | Secondary text |
| `slate-500` `#64748b` | `slate-950` | 3.1:1 | ❌ FAIL | ⚠️ large only | **Text use prohibited** |
| `slate-500` `#64748b` | `slate-800` | 2.1:1 | ❌ FAIL | ❌ FAIL | **Text use prohibited** |
| `slate-400` `#94a3b8` | `slate-900/40` | ~3.8:1 | ⚠️ borderline | ✅ AA | Secondary/meta only |
| `slate-300` `#cbd5e1` | `slate-900/40` | ~8.4:1 | ✅ AAA | ✅ AAA | Card body text |
| `cyan-400` `#22d3ee` | `slate-950` | 7.4:1 | ✅ AAA | ✅ AAA | Nav active, links, metric |
| `cyan-500` `#06b6d4` (as bg) | `slate-950` text on it | 4.3:1 | ⚠️ borderline† | ✅ AA | Button label |
| `violet-400` `#a78bfa` | `slate-950` | 5.6:1 | ✅ AA | ✅ AA | Upload metric |
| `amber-400` `#fbbf24` | `slate-950` | 9.3:1 | ✅ AAA | ✅ AAA | Ping metric |
| `emerald-400` `#34d399` | `slate-950` | 8.2:1 | ✅ AAA | ✅ AAA | Jitter metric |
| `orange-400` `#fb923c` | `slate-950` | 5.2:1 | ✅ AA | ✅ AA | Alerts |
| `red-400` `#f87171` | `slate-950` | 5.1:1 | ✅ AA | ✅ AA | Errors |
| `slate-600` `#475569` | transparent/dark | ~3.4:1 | ✅ 1.4.11 | ✅ | Scrollbar thumb |

† Passes at `font-medium` / 14px+. Do not use below this spec.

---

## 4. Typography

Font family: **Inter** — `font-family: 'Inter', system-ui, sans-serif`
Anti-aliasing: `-webkit-font-smoothing: antialiased`

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />
```

| Style | Tailwind classes | Example |
|---|---|---|
| Display (metric value) | `text-3xl md:text-4xl font-bold tracking-tighter` | `95.3` |
| Page title | `text-2xl font-bold text-slate-100` | `Dashboard` |
| Section heading | `text-lg font-semibold text-slate-200` | `Performance History` |
| Card heading | `text-base font-semibold text-slate-200` | `Test Interval` |
| Sub-section heading | `text-sm font-medium text-slate-300` | `Webhook` |
| Body / description | `text-sm text-slate-300` | `Scheduler running · last run…` |
| Form label | `text-sm font-medium text-slate-300` | `Interval (minutes)` |
| Helper / caption | `text-xs text-slate-400` | `Minimum 5 minutes.` |
| Table header | `text-xs font-medium uppercase tracking-wider text-slate-400` | `DATE & TIME` |
| Monospace data | `font-mono font-medium text-slate-200` | `04:22` |
| Badge / pill text | `text-xs` | `24 entries` |

> **Changed from original:**mi
`body/description` promoted from `text-slate-400` →
`text-slate-300` on card surfaces.
`helper/caption` promoted from `text-slate-500` → `text-slate-400`.

---

## 5. Spacing & Layout

| Token | Value | Usage |
|---|---|---|
| Header height | `h-14` (56px) | Fixed top bar |
| Sidebar width | `w-56` (224px) | Desktop left sidebar |
| Page max-width | `max-w-6xl` | Dashboard content area |
| Settings max-width | `max-w-3xl` | Settings page |
| Content padding (mobile) | `p-4` | Main content wrapper |
| Content padding (desktop) | `md:p-6` | Main content wrapper |
| Section gap | `space-y-6` | Between top-level page sections |
| Card padding | `p-6` | Standard card interior |
| Card border-radius | `rounded-2xl` | Cards, metric tiles |
| Panel border-radius | `rounded-xl` | Collapsible panels (Result Log) |
| Input border-radius | `rounded-lg` | Text inputs, textareas |
| Badge border-radius | `rounded-full` | Pills and status chips |
| Badge border-radius (chip) | `rounded-md` | Inline status badges (e.g. "Test Running") |

---

## 6. Borders & Surfaces

```css
/* Card */
bg-slate-900/40  border border-slate-800  rounded-2xl

/* Panel */
bg-slate-900/30  border border-slate-800  rounded-xl

/* Row item */
bg-slate-800/30  border border-slate-700/50  rounded-lg

/* Header */
bg-slate-950/90  border-b border-slate-800  backdrop-blur

/* Sidebar */
bg-slate-950/50  border-r border-slate-800

/* Input */
bg-slate-950  border border-slate-700  rounded-lg

/* Divider (within cards) */
border-t border-slate-700
```

---

## 7. Components

### 7.1 Buttons

#### Primary

```css
bg-cyan-500 hover:bg-cyan-400 text-slate-950
shadow-lg shadow-cyan-500/20
px-4 py-2 rounded-lg font-medium transition-all
```

> Button label text: `text-slate-950` on `bg-cyan-500` = 4.3:1 (AA at font-medium 14px+). Do not reduce below this spec.

#### Ghost / Tinted (cyan)

```css
bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400
border border-cyan-500/30
px-4 py-2 rounded-lg font-medium transition-all
```

#### Success state

```css
bg-emerald-500/20 text-emerald-400 border border-emerald-500/30
```

#### Error state

```css
bg-red-500/10 text-red-400 border border-red-500/20
```

#### Disabled

```css
bg-slate-800 text-slate-500 cursor-not-allowed
```

> Note: `slate-500` is acceptable here because disabled text is intentionally non-readable per WCAG
(disabled elements are exempt from contrast requirements under 1.4.3).

#### Icon-only

```css
p-2 rounded-md text-slate-400
hover:text-slate-200 hover:bg-slate-800/50 transition-colors
```

> **Required:** every icon-only button must have `aria-label="[action description]"`. Examples: `aria-label="Show API key"`,
`aria-label="Export CSV"`, `aria-label="Collapse result log"`.

---

### 7.2 Inputs & Textareas

Base classes shared by all inputs:

```css
bg-slate-950 border border-slate-700 rounded-lg
px-4 py-2 text-slate-200
placeholder:text-slate-400
focus:outline-none focus:ring-1 transition-all
```

> **Changed from original:** `placeholder:text-slate-500` →
`placeholder:text-slate-400` (fixes 2.1:1 contrast failure on hover state).

Focus ring color varies by section:

| Context | Focus border / ring |
|---|---|
| General / Settings | `focus:border-cyan-500 focus:ring-cyan-500` |
| API Key | `focus:border-amber-500 focus:ring-amber-500` |
| Alerts | `focus:border-orange-500 focus:ring-orange-500` |

Monospace textarea (Apprise URLs):

```css
font-mono  /* added to the base classes above */
```

---

### 7.3 Toggles

Large (h-5 w-9) — used for exporters and alerts master toggle:

```jsx
<button
  role="switch"
  aria-checked={enabled}
  aria-label="Enable CSV Export"
  onClick={() => setEnabled(!enabled)}
  className={cn(
    "relative inline-flex h-5 w-9 items-center rounded-full transition-colors",
    enabled ? "bg-cyan-500" : "bg-slate-700"
  )}
>
  <span
    className={cn(
      "inline-block h-3 w-3 rounded-full bg-white transition-transform",
      enabled ? "translate-x-5" : "translate-x-1"
    )}
  />
</button>
```

Small (h-4 w-8) — used for alert providers:

```jsx
// Same pattern, different sizing:
// h-4 w-8 · thumb: h-2.5 w-2.5
// enabled: translate-x-4.5 · disabled: translate-x-1
```

Toggle-on color by context:

| Context | Active color |
|---|---|
| Exporters / Webhook / Gotify / ntfy / Apprise | `bg-cyan-500` |
| Alerts master toggle | `bg-orange-500` |

> **ARIA required:** `role="switch"` and `aria-checked={boolean}` must be present on every toggle.
Screen readers announce the element as a switch with on/off state.
`aria-label` must describe the specific setting being toggled.

---

### 7.4 Badges & Pills

| Variant | Classes |
|---|---|
| Default count/label | `text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700` |
| Version mono | `text-xs px-2 py-0.5 rounded-full bg-slate-800/60 text-slate-400 border border-slate-700/50 font-mono` |
| Status chip (active) | `text-xs px-2 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-medium` |
| Update available | `text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30` |

> **Changed from original:** version badge `text-slate-500` → `text-slate-400`.

---

### 7.5 Alert Banners

```css
flex items-center gap-2 px-4 py-3 rounded-lg text-sm
```

| Type | Background | Border | Text |
|---|---|---|---|
| Error | `bg-red-500/10` | `border-red-500/20` | `text-red-400` |
| Success | `bg-emerald-500/10` | `border-emerald-500/20` | `text-emerald-400` |
| Warning | `bg-amber-500/10` | `border-amber-500/20` | `text-amber-400` |

---

### 7.6 Navigation Links

```css
flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all
```

| State | Classes |
|---|---|
| Active | `bg-cyan-500/10 text-cyan-400 border border-cyan-500/20` |
| Inactive | `text-slate-400 hover:text-slate-200 hover:bg-slate-800/50` |

---

### 7.7 Metric Cards (SpeedGauge)

Each metric card is a `rounded-2xl border bg-slate-900/50` with a thin top accent strip:

```css
relative overflow-hidden rounded-2xl border {metric.border} bg-slate-900/50 p-5
flex flex-col items-center justify-center text-center
```

Top accent strip:

```css
absolute top-0 left-0 w-full h-0.5 {metric.bg}
```

Icon container:

```css
p-2.5 rounded-full {metric.bg} {metric.color} mb-3
```

| Metric | Text color | Background tint | Border | Label color |
|---|---|---|---|---|
| Download | `text-cyan-400` | `bg-cyan-500/10` | `border-cyan-500/20` | `text-slate-400` |
| Upload | `text-violet-400` | `bg-violet-500/10` | `border-violet-500/20` | `text-slate-400` |
| Ping | `text-amber-400` | `bg-amber-500/10` | `border-amber-500/20` | `text-slate-400` |
| Jitter | `text-emerald-400` | `bg-emerald-500/10` | `border-emerald-500/20` | `text-slate-400` |

> **Changed from original:** metric label color `text-slate-500` → `text-slate-400`.

---

### 7.8 Result Log / Collapsible Panel

The Result Log is a collapsible panel with a header row, badge count, export action, and animated body.

**Panel header:**

```css
flex items-center justify-between px-6 py-4
```

| Element | Classes |
|---|---|
| Title | `text-lg font-semibold text-slate-200` |
| Entry count badge | `text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700` |
| Export CSV button | Ghost/tinted button variant (cyan) |
| Collapse chevron | Icon-only button — requires `aria-label="Collapse result log"` and `aria-expanded={open}` |

**Collapse animation:**

```jsx
<AnimatePresence>
  {open && (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: "auto", opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
    >
      {/* table content */}
    </motion.div>
  )}
</AnimatePresence>
```

**Data table inside panel:**

| Element | Classes |
|---|---|
| Table header row | `text-xs font-medium uppercase tracking-wider text-slate-400 border-b border-slate-700` |
| Table header cell | `px-4 py-3` |
| Table body row | `border-b border-slate-800 hover:bg-slate-800/30 transition-colors` |
| Table body cell | `px-4 py-3 text-sm text-slate-300` |
| Monospace data cell | `font-mono text-slate-200` |
| Failed result row | `bg-red-500/5 border-red-500/10` with `text-red-400` for status cell |

---

### 7.9 Settings Section Icons

| Section | Icon | Color |
|---|---|---|
| Test Interval | `Clock` | `text-cyan-400` |
| Exporters | `Database` | `text-violet-400` |
| Alerts | `Bell` | `text-orange-400` |
| API Key | `Key` | `text-amber-400` |

---

## 8. Charts (Recharts)

```jsx
<LineChart strokeWidth={2} dot={false}>
  <CartesianGrid
    strokeDasharray="3 3"
    stroke="#1e293b"
    vertical={false}
  />
```

### 8.1 Line Colors

| Series | Hex | Token |
|---|---|---|
| Download | `#22d3ee` | `cyan-400` |
| Upload | `#a78bfa` | `violet-400` |
| Ping | `#fbbf24` | `amber-400` |

> Jitter is not included in the Performance History chart. It is displayed as a metric card only.

### 8.2 Active Dot

```jsx
activeDot={{ r: 5, stroke: '#0f172a', strokeWidth: 2 }}
```

### 8.3 Axes

```jsx
// Shared axis props
stroke="#64748b"    // slate-500 — acceptable for non-text decorative axis lines
fontSize={12}
tickLine={false}
axisLine={false}

// XAxis
dy={10}

// YAxis
dx={-10}
// left margin: -20
```

> Note: `slate-500` is used here for the axis **tick labels** —
these should be `text-slate-400` / `#94a3b8`.
Update tick `fill` to `#94a3b8`. The axis **line** itself (`stroke`)
can remain `slate-500` as it is a non-text decorative element.

### 8.4 Tooltip

```css
/* Container */
bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl

/* Label */    text-slate-300 text-sm
/* Server */   text-slate-400 text-xs
/* Name */     text-slate-400
/* Value */    font-medium text-slate-200
/* Dot */      w-2 h-2 rounded-full (series color)
```

---

## 9. Scrollbar

```css
scrollbar-width: thin;
scrollbar-color: #475569 transparent; /* slate-600 thumb — updated from slate-700 */

::-webkit-scrollbar        { width: 6px; height: 6px; }
::-webkit-scrollbar-track  { background: transparent; }
::-webkit-scrollbar-thumb  {
  background-color: #475569; /* slate-600, was #334155 slate-700 */
  border-radius: 9999px;
}
```

> **Changed from original:** thumb color `#334155` (slate-700, 1.6:1) →
`#475569` (slate-600, ~3.4:1). Meets WCAG 1.4.11 Non-text Contrast.

---

## 10. Motion Patterns (Framer Motion)

### 10.1 Standard Patterns

| Pattern | Props |
|---|---|
| Page enter | `initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}` |
| Card / section enter | `initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}` |
| Staggered metric cards | `transition={{ delay: i * 0.08 }}` |
| Mobile sidebar | `initial={{ x: '-100%' }} animate={{ x: 0 }}` · `type: 'tween', duration: 0.22` |
| Collapsible panel | `height: 0 → 'auto'` + `opacity: 0 → 1` via `AnimatePresence` |
| Overlay backdrop | `opacity: 0 → 1` |

### 10.2 Standard Duration Tokens

| Name | Value | Used for |
|---|---|---|
| Fast | `0.15s` | Hover color transitions, toggle state |
| Default | `0.20s` | Card enter, collapse, sidebar |
| Slow | `0.30s` | Page enter, staggered sequences |
| Stagger step | `0.08s` | Per-card delay in metric grid |

### 10.3 Tailwind Animation Utilities

| Class | Usage |
|---|---|
| `animate-spin` | Activity icon while test is running |
| `animate-pulse` | Metric value and clock icon when almost due |

### 10.4 Reduced Motion

All animations must respect `prefers-reduced-motion`. Use Framer Motion's `useReducedMotion()` hook:

```jsx
import { useReducedMotion } from 'framer-motion';

function MyComponent() {
  const reduceMotion = useReducedMotion();

  const variants = {
    hidden: { opacity: 0, y: reduceMotion ? 0 : 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <motion.div
      variants={variants}
      initial="hidden"
      animate="visible"
      transition={{ duration: reduceMotion ? 0 : 0.2 }}
    >
      ...
    </motion.div>
  );
}
```

Fallback behaviour when reduced motion is preferred: instant opacity transition only, no translate, no stagger delay.

---

## 11. Empty & Loading States

### Empty state

```css
text-center py-20 text-slate-400
/* Icon: */ w-10 h-10 mx-auto mb-3 opacity-30
/* Heading: */ text-lg
/* Sub-text: */ text-sm mt-1  /* accent word: text-cyan-400 font-medium */
```

### Loading / config not ready

```css
text-slate-400 text-sm py-10 text-center
```

> **Changed from original:** `text-slate-500` → `text-slate-400` for all empty and loading state text.

### Loading spinner (inline)

```css
w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin
```

---

## 12. Logo & Brand Rules

The Hermes mark is a circular emblem containing a stylized winged foot
(Hermes/Mercury motif) with circuit-board speed lines trailing to the left.
The speed lines use all four metric colors — this is intentional and should be treated as a brand element, not decoration.

### 12.1 Logo Anatomy

| Element | Color | Notes |
|---|---|---|
| Outer ring | `#22d3ee` (cyan-400) | Matches primary accent |
| Inner field | `#0a0e1a` (near-black) | Darker than slate-950 |
| Winged foot outline | `#22d3ee` (cyan-400) | Neon line art |
| Speed line 1 (top) | `#22d3ee` | Download / cyan |
| Speed line 2 | `#a78bfa` | Upload / violet |
| Speed line 3 | `#8b5cf6` | Violet mid |
| Speed line 4 | `#22d3ee` / `#06b6d4` | Cyan variant |
| Speed line 5 | `#fbbf24` | Ping / amber |
| Lower lines | gradient violet→cyan | Decorative, follows metric palette |

The four metric colors appearing in the logo speed lines is the
visual connection between the brand mark and the data the app displays.
Preserve this when resizing or reproducing the mark.

### 12.2 Wordmark Color by Background

| Background | Logo treatment |
|---|---|
| Dark (`#0f172a`, `#141414`) | Full color — cyan ring + neon foot |
| Light surface | Not recommended — this is a dark-only mark. Use on dark bg only. |
| On cyan surface | Use white/light version if created; avoid full-color on cyan |

### 12.3 Minimum Sizes

| Context | Minimum |
|---|---|
| Emblem (screen) | 24×24px |
| Emblem (print) | 6mm |
| In-app nav (current) | 28×28px — appropriate |

### 12.4 Clear Space

Maintain clear space equal to the emblem height on all sides. No other text or icons within this zone.

### 12.5 Prohibited Uses

- Do not recolor the cyan outline to any other color
- Do not remove or recolor the speed lines — they carry semantic meaning (metric colors)
- Do not place on light backgrounds without a dedicated light-mode variant
- Do not add drop shadows or glows beyond what is in the original asset
- Do not stretch or distort the aspect ratio

---

## 13. AI Assistance Notes

This section provides direct rules for AI code generation tools
(Claude, Copilot, Cursor, etc.) to generate on-brand, accessible Hermes UI code.

### When generating Hermes UI components

**Typography:**

- Always use `font-family: 'Inter', system-ui, sans-serif` with `-webkit-font-smoothing: antialiased`
- Page titles: `text-2xl font-bold text-slate-100`
- Card headings: `text-base font-semibold text-slate-200`
- Body/description text: `text-sm text-slate-300` (on card surfaces) or `text-sm text-slate-400` (on page bg)
- Helper/caption: `text-xs text-slate-400` — never `text-slate-500` for readable text

**Color rules:**

- Never use `text-slate-500` for any readable text — it fails WCAG AA
- Minimum text color on `slate-950` bg: `slate-400` (#94a3b8)
- Minimum text color on `slate-900/40` card bg: `slate-300` (#cbd5e1)
- `slate-500` is permitted only for decorative non-text elements (borders, dividers, disabled states, decorative axis lines)
- All placeholder text: `placeholder:text-slate-400` — never `placeholder:text-slate-500`
- Scrollbar thumb: `#475569` (slate-600) — not `#334155` (slate-700)

**Accent colors — semantic rules:**

- `cyan-400` / `cyan-500` — primary accent, download metric, interactive actions
- `violet-400` — upload metric only
- `amber-400` — ping metric, warnings, API key context
- `emerald-400` — jitter metric, success states
- `orange-400` — alerts (user-configured notifications) only
- `red-400` — system/test failures only. Never use red for alert notifications.

**Components:**

- All toggles require: `role="switch"` `aria-checked={boolean}` `aria-label="[setting name]"`
- All icon-only buttons require: `aria-label="[action]"`
- All collapsible sections require: `aria-expanded={boolean}` on the trigger
- Buttons: `rounded-lg` — not `rounded-full` or `rounded-xl`
- Cards: `rounded-2xl`
- Inputs: `rounded-lg` with `placeholder:text-slate-400`
- Tint chips/badges: `rounded-full` for pills, `rounded-md` for inline status chips

**Surfaces:**

- This is a dark-mode-only app. Always use dark backgrounds.
- Card surface: `bg-slate-900/40 border border-slate-800 rounded-2xl`
- Never add `box-shadow` glow effects beyond the existing `shadow-cyan-500/20` button shadow
- No `backdrop-blur` except on the fixed header

**Motion:**

- Always include `useReducedMotion()` check for any Framer Motion animation
- Standard duration: 200ms. Fast: 150ms. Slow: 300ms.
- Stagger delay: `i * 0.08s` for metric card grids

**Copy tone:**

- Terse, technical, data-forward
- Prefer: "Scheduler running", "Last run", "ms", "Mbps", "42 entries"
- Avoid: marketing language, decorative descriptions, emoji in UI text

---

## 14. Changelog

### Current (post-audit)

- **Accessibility fixes (4 token changes):**
  - `text-slate-500` → `text-slate-400` for all readable text
  (helper, caption, chart axes, metric labels, version badge, empty states)
  - `placeholder:text-slate-500` → `placeholder:text-slate-400` on all inputs and textareas
  - Scrollbar thumb `#334155` (slate-700) → `#475569` (slate-600) — fixes WCAG 1.4.11
  - Card body text minimum raised to `text-slate-300` on semi-transparent card surfaces
- **Added:** toggle ARIA pattern (`role="switch"`, `aria-checked`, `aria-label`) with real JSX snippet
- **Added:** icon-only button `aria-label` requirement documented
- **Added:** `useReducedMotion()` pattern in motion section
- **Added:** animation duration tokens (fast/default/slow/stagger)
- **Added:** Result Log / collapsible panel component specification
- **Added:** data table component specification with failed row state
- **Added:** Logo & brand rules section
- **Added:** AI assistance notes section
- **Added:** Jitter chart line clarification (not in Performance History chart)
- **Added:** red vs orange semantic boundary definition
- **Added:** disabled color pattern for colored elements
- **Fixed:** all code fence closing tags corrected (removed erroneous language tag on closing fences)
- **Fixed:** toggle component replaced pseudo-code with real JSX using conditional classes
- **Fixed:** chart section separated into Recharts props and style values subsections
- **Fixed:** stack table updated with version column

### Original (pre-audit)

- Initial style guide covering stack, color palette,
typography, spacing, borders, components, charts, scrollbar, and motion patterns

---

### Hermes Style Guide · Post-audit revision · 2026*
