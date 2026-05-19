---
layout: default
title: Style Guide
nav_order: 99
---

# Hermes Style Guide

Design tokens, component patterns, and conventions used across the Hermes frontend.

---

## Stack

| Concern | Tool |
|---|---|
| Styling | Tailwind CSS v3 |
| Component framework | React 18 + TypeScript |
| Animation | Framer Motion |
| Icons | Lucide React |
| Charts | Recharts |
| Font | Inter (Google Fonts, weights 300–800) |

---

## Color Palette

### Base / Backgrounds

| Token | Hex | Usage |
|---|---|---|
| `slate-950` | `#0f172a` | App background, header, sidebar |
| `slate-900/40` | `#0f172a66` | Card surface |
| `slate-900/50` | `#0f172a80` | Metric card surface |
| `slate-800` | `#1e293b` | Borders, hover surfaces, chart grid |
| `slate-700` | `#334155` | Input borders, muted borders, scrollbar thumb |

### Text

| Token | Hex | Usage |
|---|---|---|
| `slate-100` | `#f1f5f9` | Primary text, page titles |
| `slate-200` | `#e2e8f0` | Section/card headings, table data |
| `slate-300` | `#cbd5e1` | Form labels, table cell text |
| `slate-400` | `#94a3b8` | Secondary text, nav inactive, body copy |
| `slate-500` | `#64748b` | Muted text, placeholders, chart axes |

### Accent / Semantic

| Token | Hex | Role | Used for |
|---|---|---|---|
| `cyan-400` | `#22d3ee` | Primary accent | Download metric, nav active, links |
| `cyan-500` | `#06b6d4` | Primary action | Primary button, toggle-on (default) |
| `violet-400` | `#a78bfa` | Upload | Upload metric, Exporters icon |
| `amber-400` | `#fbbf24` | Warning / Ping | Ping metric, countdown clock |
| `emerald-400` | `#34d399` | Success / Jitter | Jitter metric, success states |
| `orange-400` | `#fb923c` | Alerts | Alerts section icon, toggle-on |
| `red-400` | `#f87171` | Error | Error banners, failed states |

---

## Typography

Font family: **Inter** — `font-family: 'Inter', system-ui, sans-serif`  
Anti-aliasing: `-webkit-font-smoothing: antialiased`

| Style | Tailwind classes | Example |
|---|---|---|
| Display (metric value) | `text-3xl md:text-4xl font-bold tracking-tighter` | `95.3` |
| Page title | `text-2xl font-bold text-slate-100` | `Dashboard` |
| Section heading | `text-lg font-semibold text-slate-200` | `Performance History` |
| Card heading | `text-base font-semibold text-slate-200` | `Test Interval` |
| Sub-section heading | `text-sm font-medium text-slate-300` | `Webhook` |
| Body / description | `text-sm text-slate-400` | `Scheduler running · last run…` |
| Form label | `text-sm font-medium text-slate-300` | `Interval (minutes)` |
| Helper / caption | `text-xs text-slate-500` | `Minimum 5 minutes.` |
| Table header | `text-xs font-medium uppercase tracking-wider text-slate-400` | `DATE & TIME` |
| Monospace data | `font-mono font-medium text-slate-200` | `04:22` |
| Badge / pill text | `text-xs` | `24 entries` |

---

## Spacing & Layout

| Token | Value | Usage |
|---|---|---|
| Header height | `h-14` (56 px) | Fixed top bar |
| Sidebar width | `w-56` (224 px) | Desktop left sidebar |
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

## Borders & Surfaces

```text
Card:      bg-slate-900/40  border border-slate-800  rounded-2xl
Panel:     bg-slate-900/30  border border-slate-800  rounded-xl
Row item:  bg-slate-800/30  border border-slate-700/50  rounded-lg
Header:    bg-slate-950/90  border-b border-slate-800  backdrop-blur
Sidebar:   bg-slate-950/50  border-r border-slate-800
Input:     bg-slate-950     border border-slate-700  rounded-lg
Divider:   border-t border-slate-700  (within cards)
```text

---

## Components

### Buttons

#### Primary

```text
bg-cyan-500 hover:bg-cyan-400 text-slate-950
shadow-lg shadow-cyan-500/20
px-4 py-2 rounded-lg font-medium transition-all
```text

#### Ghost / Tinted (cyan)

```text
bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400
border border-cyan-500/30
px-4 py-2 rounded-lg font-medium transition-all
```text

#### Success state

```text
bg-emerald-500/20 text-emerald-400 border border-emerald-500/30
```text

#### Error state

```text
bg-red-500/10 text-red-400 border border-red-500/20
```text

#### Disabled

```text
bg-slate-800 text-slate-500 cursor-not-allowed
```text

#### Icon-only

```text
p-2 rounded-md text-slate-400
hover:text-slate-200 hover:bg-slate-800/50 transition-colors
```text

---

### Inputs & Textareas

Base classes shared by all inputs:

```text
bg-slate-950 border border-slate-700 rounded-lg
px-4 py-2 text-slate-200
focus:outline-none focus:ring-1 transition-all
```text

Focus ring color varies by section:

| Context | Focus border/ring |
|---|---|
| General / Settings | `focus:border-cyan-500 focus:ring-cyan-500` |
| API Key | `focus:border-amber-500 focus:ring-amber-500` |
| Alerts | `focus:border-orange-500 focus:ring-orange-500` |

Monospace textarea (Apprise URLs):

```text
font-mono  (added to the base classes above)
```text

---

### Toggles

Large (h-5 w-9) — used for exporters and alerts master toggle:

```html
<button class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors
               [on: bg-cyan-500] [off: bg-slate-700]">
  <span class="inline-block h-3 w-3 rounded-full bg-white transition-transform
               [on: translate-x-5] [off: translate-x-1]" />
</button>
```text

Small (h-4 w-8) — used for alert providers:

```text
h-4 w-8  thumb: h-2.5 w-2.5  [on: translate-x-4.5] [off: translate-x-1]
```text

Toggle-on color by context:

| Context | Active color |
|---|---|
| Exporters / Webhook / Gotify / ntfy / Apprise | `bg-cyan-500` |
| Alerts master toggle | `bg-orange-500` |

---

### Badges & Pills

| Variant | Classes |
|---|---|
| Default count/label | `text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700` |
| Version mono | `text-xs px-2 py-0.5 rounded-full bg-slate-800/60 text-slate-500 border border-slate-700/50 font-mono` |
| Status chip (active) | `text-xs px-2 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-medium` |
| Update available | `text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30` |

---

### Alert Banners

```text
flex items-center gap-2 px-4 py-3 rounded-lg text-sm
```text

| Type | Background | Border | Text |
|---|---|---|---|
| Error | `bg-red-500/10` | `border-red-500/20` | `text-red-400` |
| Success | `bg-emerald-500/10` | `border-emerald-500/20` | `text-emerald-400` |
| Warning | `bg-amber-500/10` | `border-amber-500/20` | `text-amber-400` |

---

### Navigation Links

```text
flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all
```text

| State | Classes |
|---|---|
| Active | `bg-cyan-500/10 text-cyan-400 border border-cyan-500/20` |
| Inactive | `text-slate-400 hover:text-slate-200 hover:bg-slate-800/50` |

---

### Metric Cards (SpeedGauge)

Each metric card is a `rounded-2xl border bg-slate-900/50` with a thin top accent strip:

```text
relative overflow-hidden rounded-2xl border {metric.border} bg-slate-900/50 p-5
flex flex-col items-center justify-center text-center
```text

Top accent strip: `absolute top-0 left-0 w-full h-0.5 {metric.bg}`

Icon container: `p-2.5 rounded-full {metric.bg} {metric.color} mb-3`

| Metric | Text color | Background tint | Border |
|---|---|---|---|
| Download | `text-cyan-400` | `bg-cyan-500/10` | `border-cyan-500/20` |
| Upload | `text-violet-400` | `bg-violet-500/10` | `border-violet-500/20` |
| Ping | `text-amber-400` | `bg-amber-500/10` | `border-amber-500/20` |
| Jitter | `text-emerald-400` | `bg-emerald-500/10` | `border-emerald-500/20` |

---

### Settings Section Icons

| Section | Icon | Color |
|---|---|---|
| Test Interval | `Clock` | `text-cyan-400` |
| Exporters | `Database` | `text-violet-400` |
| Alerts | `Bell` | `text-orange-400` |
| API Key | `Key` | `text-amber-400` |

---

## Charts (Recharts)

```text
LineChart · strokeWidth 2 · dot={false}
CartesianGrid strokeDashcolor="3 3" stroke="#1e293b" vertical={false}
```text

### Line colors

| Series | Hex | Tailwind |
|---|---|---|
| Download | `#22d3ee` | `cyan-400` |
| Upload | `#a78bfa` | `violet-400` |
| Ping | `#fbbf24` | `amber-400` |

### Active dot

```text
r: 5  stroke: #0f172a (slate-950)  strokeWidth: 2
```text

### Axes

```text
stroke: #64748b (slate-500)  fontSize: 12  tickLine: false  axisLine: false
XAxis dy: 10   YAxis dx: -10  left margin: -20
```text

### Tooltip

```text
bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl
Label:   text-slate-300 text-sm
Server:  text-slate-500 text-xs
Name:    text-slate-400
Value:   font-medium text-slate-200
Dot:     w-2 h-2 rounded-full (series color)
```text

---

## Scrollbar

```css
scrollbar-width: thin;
scrollbar-color: #334155 transparent;   /* slate-700 thumb */

::-webkit-scrollbar        { width: 6px; height: 6px; }
::-webkit-scrollbar-track  { background: transparent; }
::-webkit-scrollbar-thumb  { background-color: #334155; border-radius: 9999px; }
```text

---

## Motion Patterns (Framer Motion)

| Pattern | Props |
|---|---|
| Page enter | `initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}` |
| Card / section enter | `initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}` |
| Staggered metric cards | `transition={{ delay: i * 0.08 }}` |
| Mobile sidebar | `initial={{ x: '-100%' }} animate={{ x: 0 }}` · `type: 'tween', duration: 0.22` |
| Collapsible panel | `height: 0 → 'auto'` + `opacity: 0 → 1` via `AnimatePresence` |
| Overlay backdrop | `opacity: 0 → 1` |

Tailwind animation utilities also in use:

| Class | Usage |
|---|---|
| `animate-spin` | Activity icon while test is running |
| `animate-pulse` | Metric value and clock icon when almost due |

---

## Empty & Loading States

```text
text-center py-20 text-slate-500
Icon: 40px, mx-auto mb-3 opacity-30
Heading: text-lg
Sub-text: text-sm mt-1  (accent word in text-cyan-400 font-medium)
```text

Loading / config not ready:

```text
text-slate-500 text-sm py-10 text-center
```text

Loading spinner (inline):

```text
w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin
```text
