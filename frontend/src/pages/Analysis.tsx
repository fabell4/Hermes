import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { AlertTriangle, TrendingDown, TrendingUp, Clock, BarChart2, Minus } from 'lucide-react'
import type {
  AnnotatedResult,
  AnomalyFlag,
  HourlyStats,
  TrendReport,
} from '@/types'

const API = import.meta.env.VITE_API_BASE ?? ''

type Tab = 'anomalies' | 'time-of-day' | 'trends'

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function MetricBadge({ metric }: { readonly metric: string }) {
  const labels: Record<string, string> = {
    download_mbps: 'Download',
    upload_mbps: 'Upload',
    ping_ms: 'Ping',
  }
  return (
    <span className="px-1.5 py-0.5 rounded text-xs bg-amber-500/10 border border-amber-500/20 text-amber-400 font-mono">
      {labels[metric] ?? metric}
    </span>
  )
}

function SlopeIndicator({ slope, invert = false }: { readonly slope: number | null; readonly invert?: boolean }) {
  if (slope === null) return <span className="text-slate-500 text-sm">—</span>
  const isGood = invert ? slope < 0 : slope > 0
  const isNeutral = Math.abs(slope) < 0.01
  if (isNeutral) return <span className="flex items-center gap-1 text-slate-400 text-sm"><Minus size={14} />{slope.toFixed(3)}</span>
  return isGood
    ? <span className="flex items-center gap-1 text-emerald-400 text-sm"><TrendingUp size={14} />{slope > 0 ? '+' : ''}{slope.toFixed(3)}</span>
    : <span className="flex items-center gap-1 text-red-400 text-sm"><TrendingDown size={14} />{slope.toFixed(3)}</span>
}

// ---------------------------------------------------------------------------
// Anomalies tab
// ---------------------------------------------------------------------------

interface AnomaliesTabProps {
  readonly data: AnnotatedResult[]
  readonly loading: boolean
  readonly error: string | null
}

function FlagDetail({ flags }: { readonly flags: AnomalyFlag[] }) {
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {flags.map((f) => (
        <span
          key={f.metric}
          title={`z=${f.z_score} (mean ${f.baseline_mean} ± ${f.baseline_stdev})`}
          className="flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-red-500/10 border border-red-500/20 text-red-300"
        >
          <MetricBadge metric={f.metric} />
          <span className="opacity-75">z={f.z_score.toFixed(1)}</span>
        </span>
      ))}
    </div>
  )
}

function AnomaliesTab({ data, loading, error }: AnomaliesTabProps) {
  if (loading) return <p className="text-slate-400 text-sm">Loading…</p>
  if (error) return <p className="text-red-400 text-sm">{error}</p>

  const anomalous = data.filter((r) => r.is_anomaly)
  const pct = data.length > 0 ? ((anomalous.length / data.length) * 100).toFixed(1) : '0'

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 flex-wrap">
        <div className="px-4 py-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-slate-500 mb-0.5">Anomalies (last 50)</p>
          <p className="text-2xl font-bold text-amber-400">{anomalous.length}</p>
        </div>
        <div className="px-4 py-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-slate-500 mb-0.5">Anomaly rate</p>
          <p className="text-2xl font-bold text-slate-200">{pct}%</p>
        </div>
      </div>

      {anomalous.length === 0 && data.length > 0 && (
        <p className="text-slate-400 text-sm">No anomalies detected in the last {data.length} results.</p>
      )}

      {anomalous.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-slate-500 text-xs uppercase tracking-wide">
                <th className="text-left px-4 py-3">Time</th>
                <th className="text-right px-4 py-3">↓ Mbps</th>
                <th className="text-right px-4 py-3">↑ Mbps</th>
                <th className="text-right px-4 py-3">Ping ms</th>
                <th className="text-left px-4 py-3">Anomalous metrics</th>
              </tr>
            </thead>
            <tbody>
              {anomalous.map((r) => (
                <tr key={r.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3 text-slate-300 whitespace-nowrap">
                    {new Date(r.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-slate-200">
                    {r.download_mbps.toFixed(1)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-slate-200">
                    {r.upload_mbps.toFixed(1)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-slate-200">
                    {r.ping_ms.toFixed(1)}
                  </td>
                  <td className="px-4 py-3">
                    <FlagDetail flags={r.anomaly_flags} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Time-of-day tab
// ---------------------------------------------------------------------------

interface TimeOfDayTabProps {
  readonly data: HourlyStats[]
  readonly loading: boolean
  readonly error: string | null
}

interface TimeTooltipProps {
  readonly active?: boolean
  readonly payload?: { name: string; value: number; color: string }[]
  readonly label?: string
}

function TimeTooltip({ active, payload, label }: TimeTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl">
      <p className="text-slate-300 text-sm mb-2">{label}:00–{label}:59</p>
      {payload.map((e) => (
        <div key={e.name} className="flex items-center gap-2 text-sm">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: e.color }} />
          <span className="text-slate-400">{e.name}:</span>
          <span className="font-medium text-slate-200">
            {e.value} {e.name === 'Ping' ? 'ms' : 'Mbps'}
          </span>
        </div>
      ))}
    </div>
  )
}

function TimeOfDayTab({ data, loading, error }: TimeOfDayTabProps) {
  if (loading) return <p className="text-slate-400 text-sm">Loading…</p>
  if (error) return <p className="text-red-400 text-sm">{error}</p>
  if (data.length === 0) return <p className="text-slate-400 text-sm">No data available yet.</p>

  const chartData = data.map((h) => ({
    hour: String(h.hour).padStart(2, '0'),
    Download: h.avg_download_mbps,
    Upload: h.avg_upload_mbps,
    Ping: h.avg_ping_ms,
    samples: h.sample_count,
  }))

  return (
    <div className="space-y-6">
      <p className="text-slate-400 text-sm">
        Average speeds by hour of day (UTC). Dips reveal congestion windows.
      </p>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="hour"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              dy={8}
              label={{ value: 'Hour (UTC)', position: 'insideBottom', offset: -2, fill: '#64748b', fontSize: 11 }}
            />
            <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dx={-8} />
            <Tooltip content={<TimeTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: 12, fontSize: 12, color: '#94a3b8' }}
            />
            <Bar dataKey="Download" fill="#06b6d4" radius={[2, 2, 0, 0]} />
            <Bar dataKey="Upload" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="h-48">
        <p className="text-xs text-slate-500 mb-2">Ping latency by hour</p>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 4, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis dataKey="hour" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dy={8} />
            <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dx={-8} />
            <Tooltip content={<TimeTooltip />} />
            <Bar dataKey="Ping" fill="#f59e0b" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Trends tab
// ---------------------------------------------------------------------------

interface TrendsTabProps {
  readonly data: TrendReport | null
  readonly loading: boolean
  readonly error: string | null
}

interface TrendTooltipProps {
  readonly active?: boolean
  readonly payload?: { name: string; value: number; color: string }[]
  readonly label?: string
}

function TrendTooltip({ active, payload, label }: TrendTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl">
      <p className="text-slate-300 text-sm mb-2">{label}</p>
      {payload.map((e) => (
        <div key={e.name} className="flex items-center gap-2 text-sm">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: e.color }} />
          <span className="text-slate-400">{e.name}:</span>
          <span className="font-medium text-slate-200">
            {e.value} {e.name === 'Ping' ? 'ms' : 'Mbps'}
          </span>
        </div>
      ))}
    </div>
  )
}

function TrendsTab({ data, loading, error }: TrendsTabProps) {
  if (loading) return <p className="text-slate-400 text-sm">Loading…</p>
  if (error) return <p className="text-red-400 text-sm">{error}</p>
  if (!data || data.months_available === 0) {
    return <p className="text-slate-400 text-sm">Not enough data yet — trends appear after two months of results.</p>
  }

  const chartData = data.monthly_stats.map((m) => ({
    month: m.month,
    Download: m.avg_download_mbps,
    Upload: m.avg_upload_mbps,
    Ping: m.avg_ping_ms,
  }))

  return (
    <div className="space-y-6">
      {/* Degradation banner */}
      {data.degradation_detected && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <TrendingDown size={16} className="shrink-0" />
          Performance degradation detected — regression slope indicates worsening trend.
        </div>
      )}
      {!data.degradation_detected && data.months_available >= 2 && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
          <TrendingUp size={16} className="shrink-0" />
          No degradation detected — performance appears stable or improving.
        </div>
      )}

      {/* Slope summary */}
      {data.months_available >= 2 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { label: 'Download slope', slope: data.download_slope, invert: false },
            { label: 'Upload slope', slope: data.upload_slope, invert: false },
            { label: 'Ping slope', slope: data.ping_slope, invert: true },
          ].map(({ label, slope, invert }) => (
            <div key={label} className="px-4 py-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <p className="text-xs text-slate-500 mb-1">{label} (Mbps or ms / month)</p>
              <SlopeIndicator slope={slope} invert={invert} />
            </div>
          ))}
        </div>
      )}

      {/* Monthly trend chart */}
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis dataKey="month" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dy={8} />
            <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dx={-8} />
            <Tooltip content={<TrendTooltip />} />
            <Legend wrapperStyle={{ paddingTop: 12, fontSize: 12, color: '#94a3b8' }} />
            <Line type="monotone" dataKey="Download" stroke="#06b6d4" dot={{ r: 4 }} strokeWidth={2} />
            <Line type="monotone" dataKey="Upload" stroke="#8b5cf6" dot={{ r: 4 }} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="h-48">
        <p className="text-xs text-slate-500 mb-2">Average ping per month</p>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 4, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis dataKey="month" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dy={8} />
            <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dx={-8} />
            <Tooltip content={<TrendTooltip />} />
            <Line type="monotone" dataKey="Ping" stroke="#f59e0b" dot={{ r: 4 }} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Monthly table */}
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-slate-500 text-xs uppercase tracking-wide">
              <th className="text-left px-4 py-3">Month</th>
              <th className="text-right px-4 py-3">Samples</th>
              <th className="text-right px-4 py-3">Avg ↓ Mbps</th>
              <th className="text-right px-4 py-3">Avg ↑ Mbps</th>
              <th className="text-right px-4 py-3">Avg Ping ms</th>
            </tr>
          </thead>
          <tbody>
            {[...data.monthly_stats].reverse().map((m) => (
              <tr key={m.month} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                <td className="px-4 py-3 text-slate-300 font-mono">{m.month}</td>
                <td className="px-4 py-3 text-right text-slate-400">{m.sample_count}</td>
                <td className="px-4 py-3 text-right font-mono text-cyan-400">{m.avg_download_mbps.toFixed(1)}</td>
                <td className="px-4 py-3 text-right font-mono text-violet-400">{m.avg_upload_mbps.toFixed(1)}</td>
                <td className="px-4 py-3 text-right font-mono text-amber-400">{m.avg_ping_ms.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Analysis page
// ---------------------------------------------------------------------------

const TABS: { id: Tab; label: string; icon: React.ComponentType<{ size: number }> }[] = [
  { id: 'anomalies', label: 'Anomaly Detection', icon: AlertTriangle },
  { id: 'time-of-day', label: 'Time of Day', icon: Clock },
  { id: 'trends', label: 'Trend Analysis', icon: BarChart2 },
]

export function Analysis() {
  const [tab, setTab] = useState<Tab>('anomalies')

  const [anomalies, setAnomalies] = useState<AnnotatedResult[]>([])
  const [anomaliesLoading, setAnomaliesLoading] = useState(true)
  const [anomaliesError, setAnomaliesError] = useState<string | null>(null)

  const [hourly, setHourly] = useState<HourlyStats[]>([])
  const [hourlyLoading, setHourlyLoading] = useState(true)
  const [hourlyError, setHourlyError] = useState<string | null>(null)

  const [trends, setTrends] = useState<TrendReport | null>(null)
  const [trendsLoading, setTrendsLoading] = useState(true)
  const [trendsError, setTrendsError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    setAnomaliesLoading(true)
    setHourlyLoading(true)
    setTrendsLoading(true)

    try {
      const r = await fetch(`${API}/api/analysis/anomalies?limit=50`)
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      setAnomalies(await r.json())
      setAnomaliesError(null)
    } catch (e) {
      setAnomaliesError(e instanceof Error ? e.message : 'Failed to load anomaly data')
    } finally {
      setAnomaliesLoading(false)
    }

    try {
      const r = await fetch(`${API}/api/analysis/time-of-day?days=30`)
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      setHourly(await r.json())
      setHourlyError(null)
    } catch (e) {
      setHourlyError(e instanceof Error ? e.message : 'Failed to load time-of-day data')
    } finally {
      setHourlyLoading(false)
    }

    try {
      const r = await fetch(`${API}/api/analysis/trends?months=6`)
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      setTrends(await r.json())
      setTrendsError(null)
    } catch (e) {
      setTrendsError(e instanceof Error ? e.message : 'Failed to load trend data')
    } finally {
      setTrendsLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Analysis</h1>
        <p className="text-slate-400 text-sm mt-0.5">
          Anomaly detection, time-of-day patterns, and month-over-month trends
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 p-1 rounded-xl bg-slate-900/60 border border-slate-800 w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === id
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 md:p-6">
        {tab === 'anomalies' && (
          <AnomaliesTab data={anomalies} loading={anomaliesLoading} error={anomaliesError} />
        )}
        {tab === 'time-of-day' && (
          <TimeOfDayTab data={hourly} loading={hourlyLoading} error={hourlyError} />
        )}
        {tab === 'trends' && (
          <TrendsTab data={trends} loading={trendsLoading} error={trendsError} />
        )}
      </div>
    </motion.div>
  )
}
