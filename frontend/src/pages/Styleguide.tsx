import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Download,
  Upload,
  Activity,
  Wifi,
  Bell,
  Database,
  Clock,
  AlertCircle,
  CheckCircle,
  Save,
  Play,
  Send,
  Zap,
} from 'lucide-react'

// ─── Tokens ──────────────────────────────────────────────────────────────────

const COLORS = [
  // Backgrounds
  { name: 'slate-950', hex: '#0f172a', role: 'App background', dark: true },
  { name: 'slate-900', hex: '#0f172a99', role: 'Card surface (40%)', dark: true },
  { name: 'slate-800', hex: '#1e293b', role: 'Border / hover surface', dark: true },
  { name: 'slate-700', hex: '#334155', role: 'Input border / muted border', dark: true },
  // Text
  { name: 'slate-100', hex: '#f1f5f9', role: 'Primary text', dark: true },
  { name: 'slate-200', hex: '#e2e8f0', role: 'Section headings', dark: true },
  { name: 'slate-300', hex: '#cbd5e1', role: 'Table data', dark: true },
  { name: 'slate-400', hex: '#94a3b8', role: 'Secondary text / labels', dark: true },
  { name: 'slate-500', hex: '#64748b', role: 'Muted / placeholder', dark: true },
  // Accents
  { name: 'cyan-400', hex: '#22d3ee', role: 'Download / primary action', dark: false },
  { name: 'cyan-500', hex: '#06b6d4', role: 'Primary button / toggle-on', dark: false },
  { name: 'violet-400', hex: '#a78bfa', role: 'Upload metric', dark: false },
  { name: 'amber-400', hex: '#fbbf24', role: 'Ping / warning', dark: false },
  { name: 'emerald-400', hex: '#34d399', role: 'Jitter / success', dark: false },
  { name: 'orange-400', hex: '#fb923c', role: 'Alerts section', dark: false },
  { name: 'red-400', hex: '#f87171', role: 'Error states', dark: false },
]

const TYPE_SCALE = [
  { name: 'Display', classes: 'text-4xl font-bold tracking-tighter text-slate-100', sample: '95.3' },
  { name: 'Page title', classes: 'text-2xl font-bold text-slate-100', sample: 'Dashboard' },
  { name: 'Section heading', classes: 'text-lg font-semibold text-slate-200', sample: 'Performance History' },
  { name: 'Card heading', classes: 'text-base font-semibold text-slate-200', sample: 'Test Interval' },
  { name: 'Body', classes: 'text-sm text-slate-400', sample: 'Scheduler running · last run 9:41 AM' },
  { name: 'Label', classes: 'text-sm font-medium text-slate-300', sample: 'Interval (minutes)' },
  { name: 'Badge / caption', classes: 'text-xs text-slate-500', sample: 'Minimum 5 minutes.' },
  { name: 'Table header', classes: 'text-xs font-medium uppercase tracking-wider text-slate-400', sample: 'Date & Time' },
  { name: 'Mono (data)', classes: 'font-mono font-medium text-slate-200', sample: '04:22' },
]

const METRIC_COLORS = [
  { label: 'Download', color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', icon: Download },
  { label: 'Upload', color: 'text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/20', icon: Upload },
  { label: 'Ping', color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', icon: Activity },
  { label: 'Jitter', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', icon: Wifi },
]

// ─── Sections ────────────────────────────────────────────────────────────────

function Section({ title, children }: { readonly title: string; readonly children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-200 border-b border-slate-800 pb-2">{title}</h2>
      {children}
    </section>
  )
}

function Token({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className="text-slate-400">{label}</span>
      <code className="text-xs font-mono text-slate-300 bg-slate-800 px-2 py-0.5 rounded">{value}</code>
    </div>
  )
}

// ─── Color Palette ───────────────────────────────────────────────────────────

function ColorPalette() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
      {COLORS.map((c) => (
        <div key={c.name} className="rounded-xl overflow-hidden border border-slate-800">
          <div
            className="h-14 w-full"
            style={{ backgroundColor: c.hex }}
          />
          <div className="p-2 bg-slate-900/60">
            <p className="text-xs font-mono text-slate-200">{c.name}</p>
            <p className="text-xs text-slate-500 font-mono">{c.hex}</p>
            <p className="text-xs text-slate-400 mt-0.5">{c.role}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Typography ──────────────────────────────────────────────────────────────

function Typography() {
  return (
    <div className="space-y-4 bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
      <p className="text-xs text-slate-500 font-mono mb-4">Font: Inter · Weights: 300 400 500 600 700 800</p>
      {TYPE_SCALE.map((t) => (
        <div key={t.name} className="flex items-baseline gap-4 border-b border-slate-800/60 pb-3 last:border-0">
          <span className="w-36 shrink-0 text-xs text-slate-500">{t.name}</span>
          <span className={t.classes}>{t.sample}</span>
          <code className="ml-auto text-xs font-mono text-slate-600 hidden md:block">{t.classes}</code>
        </div>
      ))}
    </div>
  )
}

// ─── Buttons ─────────────────────────────────────────────────────────────────

function Buttons() {
  return (
    <div className="flex flex-wrap gap-3 items-center bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
      {/* Primary */}
      <button className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-500/20 transition-all">
        <Play size={16} className="fill-current" />
        Primary
      </button>

      {/* Ghost / tinted */}
      <button className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 transition-all">
        <Send size={16} />
        Ghost
      </button>

      {/* Success */}
      <button className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 transition-all">
        <CheckCircle size={16} />
        Success
      </button>

      {/* Error */}
      <button className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-red-500/10 text-red-400 border border-red-500/20 transition-all">
        <AlertCircle size={16} />
        Error
      </button>

      {/* Disabled */}
      <button disabled className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-slate-800 text-slate-500 cursor-not-allowed">
        <Save size={16} />
        Disabled
      </button>

      {/* Save (saved state) */}
      <button className="flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 transition-all">
        <CheckCircle size={17} />
        Saved
      </button>

      {/* Icon-only */}
      <button className="p-2 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors">
        <Bell size={18} />
      </button>
    </div>
  )
}

// ─── Badges & Pills ──────────────────────────────────────────────────────────

function Badges() {
  return (
    <div className="flex flex-wrap gap-3 items-center bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
      {/* Default badge */}
      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
        24 entries
      </span>

      {/* Version badge */}
      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800/60 text-slate-500 border border-slate-700/50 font-mono">
        v1.4.0
      </span>

      {/* Speed Monitor badge */}
      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
        <Zap size={10} className="inline mr-1 text-cyan-400" />
        Speed Monitor
      </span>

      {/* Status: running */}
      <span className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium">
        <Activity size={12} className="animate-spin" />
        Test Running
      </span>

      {/* Update available */}
      <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
        Update available
      </span>
    </div>
  )
}

// ─── Inputs ──────────────────────────────────────────────────────────────────

function Inputs() {
  const [val, setVal] = useState('60')
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
      {/* Default input */}
      <div className="space-y-2">
        <label htmlFor="sg-cyan-input" className="block text-sm font-medium text-slate-300">Default (cyan focus)</label>
        <input
          id="sg-cyan-input"
          type="number"
          value={val}
          onChange={(e) => setVal(e.target.value)}
          className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
        />
        <p className="text-xs text-slate-500">Minimum 5 minutes.</p>
      </div>

      {/* Amber focus */}
      <div className="space-y-2">
        <label htmlFor="sg-amber-input" className="block text-sm font-medium text-slate-300">Amber focus (API Key)</label>
        <input
          id="sg-amber-input"
          type="password"
          placeholder="Enter API key…"
          autoComplete="current-password"
          className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all"
        />
      </div>

      {/* Orange focus */}
      <div className="space-y-2">
        <label htmlFor="sg-orange-input" className="block text-sm font-medium text-slate-300">Orange focus (Alerts)</label>
        <input
          id="sg-orange-input"
          type="number"
          defaultValue="3"
          className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
        />
      </div>

      {/* Textarea */}
      <div className="space-y-2">
        <label htmlFor="sg-mono-textarea" className="block text-sm font-medium text-slate-300">Textarea (mono)</label>
        <textarea
          id="sg-mono-textarea"
          rows={3}
          placeholder="ntfy://ntfy.example.com/topic"
          className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono"
        />
      </div>
    </div>
  )
}

// ─── Toggles ─────────────────────────────────────────────────────────────────

function toggleActiveColor(isOn: boolean, index: number): string {
  if (!isOn) return 'bg-slate-700'
  return index === 2 ? 'bg-orange-500' : 'bg-cyan-500'
}

function Toggles() {
  const [states, setStates] = useState([true, false, true, false])
  const labels = ['CSV Export', 'SQLite', 'Alerts enabled', 'ntfy']

  const toggle = (i: number) => {
    setStates((s) => s.map((v, j) => (j === i ? !v : v)))
  }

  return (
    <div className="flex flex-wrap gap-6 items-center bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
      {labels.map((label, i) => (
        <div key={label} className="flex items-center gap-3">
          <span className="text-sm text-slate-300">{label}</span>
          {/* Large toggle (h-5 w-9) */}
          <button
            onClick={() => toggle(i)}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${toggleActiveColor(states[i], i)}`}
            aria-pressed={states[i]}
          >
            <span
              className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                states[i] ? 'translate-x-5' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      ))}
    </div>
  )
}

// ─── Cards ───────────────────────────────────────────────────────────────────

function Cards() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Standard card */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-2">
        <div className="flex items-center gap-2">
          <Clock size={18} className="text-cyan-400" />
          <h3 className="text-base font-semibold text-slate-200">Standard Card</h3>
        </div>
        <p className="text-sm text-slate-400">
          Used for settings sections and grouped content. Rounded-2xl, subtle bg, slate-800 border.
        </p>
      </div>

      {/* Chart / data card */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 md:p-6 space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-200">Data Card</h3>
          <span className="text-sm text-slate-400">24 samples</span>
        </div>
        <p className="text-sm text-slate-400">
          Used for Performance History / charts. Same structure, larger padding on md+.
        </p>
      </div>

      {/* Collapsible card */}
      <div className="border border-slate-800 rounded-xl bg-slate-900/30 overflow-hidden">
        <div className="w-full p-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors cursor-pointer">
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-slate-200">Collapsible Card</h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">24 entries</span>
          </div>
          <span className="text-xs text-slate-500">Result Log pattern · rounded-xl</span>
        </div>
      </div>

      {/* Metric card */}
      <div className="grid grid-cols-2 gap-3">
        {METRIC_COLORS.slice(0, 2).map((m) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`relative overflow-hidden rounded-2xl border ${m.border} bg-slate-900/50 p-4 flex flex-col items-center justify-center text-center`}
          >
            <div className={`absolute top-0 left-0 w-full h-0.5 ${m.bg}`} />
            <div className={`p-2 rounded-full ${m.bg} ${m.color} mb-2`}>
              <m.icon size={18} />
            </div>
            <div className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-0.5">
              {m.label}
            </div>
            <div className="flex items-baseline gap-1">
              <span className={`text-2xl font-bold tracking-tighter ${m.color}`}>95.3</span>
              <span className="text-slate-500 text-sm">Mbps</span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

// ─── Alerts / Banners ────────────────────────────────────────────────────────

function AlertBanners() {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
        <AlertCircle size={16} className="shrink-0" />
        Error: Could not connect to the Hermes API.
      </div>
      <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
        <CheckCircle size={16} className="shrink-0" />
        Settings saved successfully.
      </div>
      <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm">
        <Activity size={16} className="shrink-0" />
        Speed test running — results will appear shortly.
      </div>
    </div>
  )
}

// ─── Exporter Row ────────────────────────────────────────────────────────────

function ExporterRow() {
  const items = [
    { label: 'CSV Export', desc: 'Append results to a local CSV file', enabled: true, icon: Database },
    { label: 'Prometheus', desc: 'Expose metrics at /metrics for scraping', enabled: false, icon: Activity },
  ]
  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <Database size={18} className="text-violet-400" />
        <h3 className="text-base font-semibold text-slate-200">List Item Row</h3>
      </div>
      {items.map((item) => (
        <div key={item.label} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/30 border border-slate-700/50">
          <div>
            <div className="text-sm font-medium text-slate-200">{item.label}</div>
            <div className="text-xs text-slate-500">{item.desc}</div>
          </div>
          <button
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              item.enabled ? 'bg-cyan-500' : 'bg-slate-700'
            }`}
            aria-pressed={item.enabled}
          >
            <span
              className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                item.enabled ? 'translate-x-5' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      ))}
    </div>
  )
}

// ─── Layout Tokens ───────────────────────────────────────────────────────────

function LayoutTokens() {
  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 divide-y divide-slate-800">
      <Token label="Header height" value="h-14 (56px)" />
      <Token label="Sidebar width" value="w-56 (224px)" />
      <Token label="Page max-width" value="max-w-6xl" />
      <Token label="Settings max-width" value="max-w-3xl" />
      <Token label="Content padding (mobile)" value="p-4" />
      <Token label="Content padding (desktop)" value="md:p-6" />
      <Token label="Section gap" value="space-y-6" />
      <Token label="Card border-radius" value="rounded-2xl" />
      <Token label="Input border-radius" value="rounded-lg" />
      <Token label="Badge border-radius" value="rounded-full" />
      <Token label="Scrollbar width" value="6px (thin)" />
    </div>
  )
}

// ─── Motion Patterns ─────────────────────────────────────────────────────────

function MotionPatterns() {
  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 divide-y divide-slate-800">
      <Token label="Page enter" value="opacity 0→1, y 10→0" />
      <Token label="Card enter" value="opacity 0→1, y 20→0" />
      <Token label="Stagger delay" value="i * 0.08s" />
      <Token label="Mobile drawer" value="x -100%→0, tween 220ms" />
      <Token label="Collapsible panel" value="height 0→auto + opacity" />
      <Token label="Spinner" value="animate-spin (lucide icon)" />
      <Token label="Pulse" value="animate-pulse (metric value, clock icon)" />
    </div>
  )
}

// ─── Chart Tokens ─────────────────────────────────────────────────────────────

function ChartTokens() {
  const lines = [
    { label: 'Download', color: '#22d3ee', tw: 'cyan-400' },
    { label: 'Upload', color: '#a78bfa', tw: 'violet-400' },
    { label: 'Ping', color: '#fbbf24', tw: 'amber-400' },
  ]
  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-3">
      <p className="text-xs text-slate-500 font-mono">Recharts LineChart · strokeWidth 2 · no dots</p>
      {lines.map((l) => (
        <div key={l.label} className="flex items-center gap-3 text-sm">
          <div className="w-8 h-0.5 rounded" style={{ backgroundColor: l.color }} />
          <span className="text-slate-300 w-20">{l.label}</span>
          <code className="text-xs font-mono text-slate-500">{l.color}</code>
          <code className="text-xs font-mono text-slate-600">({l.tw})</code>
        </div>
      ))}
      <div className="flex items-center gap-3 text-sm border-t border-slate-800 pt-3">
        <div className="w-8 h-px border-t border-dashed" style={{ borderColor: '#1e293b' }} />
        <span className="text-slate-400 w-20">Grid</span>
        <code className="text-xs font-mono text-slate-500">#1e293b</code>
        <code className="text-xs font-mono text-slate-600">(slate-800)</code>
      </div>
      <div className="mt-1 text-xs text-slate-500 space-y-1 border-t border-slate-800 pt-3">
        <p>Tooltip: <code className="text-slate-400">bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl</code></p>
        <p>Axis: <code className="text-slate-400">stroke #64748b (slate-500) · fontSize 12 · no tick/axis lines</code></p>
      </div>
    </div>
  )
}

// ─── Nav ─────────────────────────────────────────────────────────────────────

function NavExample() {
  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-2">
      <p className="text-xs text-slate-500 font-mono mb-3">px-4 py-2.5 rounded-lg text-sm font-medium</p>
      {/* Active */}
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 w-fit">
        <Activity size={18} />
        Active link
      </div>
      {/* Inactive */}
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 w-fit cursor-pointer">
        <Database size={18} />
        Inactive link
      </div>
    </div>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────

export function Styleguide() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-5xl space-y-12 pb-16"
    >
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Style Guide</h1>
        <p className="text-slate-400 text-sm mt-0.5">
          Design tokens, components, and patterns used across Hermes UI.
        </p>
      </div>

      <Section title="Color Palette">
        <ColorPalette />
      </Section>

      <Section title="Typography">
        <Typography />
      </Section>

      <Section title="Buttons">
        <Buttons />
      </Section>

      <Section title="Badges & Pills">
        <Badges />
      </Section>

      <Section title="Inputs & Textareas">
        <Inputs />
      </Section>

      <Section title="Toggles">
        <Toggles />
      </Section>

      <Section title="Cards">
        <Cards />
      </Section>

      <Section title="List Item Rows">
        <ExporterRow />
      </Section>

      <Section title="Alert Banners">
        <AlertBanners />
      </Section>

      <Section title="Navigation">
        <NavExample />
      </Section>

      <Section title="Layout Tokens">
        <LayoutTokens />
      </Section>

      <Section title="Chart Tokens (Recharts)">
        <ChartTokens />
      </Section>

      <Section title="Motion Patterns (Framer Motion)">
        <MotionPatterns />
      </Section>
    </motion.div>
  )
}
