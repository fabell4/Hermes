import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { SpeedResult } from '@/types'

interface SpeedChartProps {
  readonly data: SpeedResult[]
}

interface ChartDataPoint {
  time: string
  Download: number
  Upload: number
  Ping: number
  serverName: string
}

interface TooltipPayloadEntry {
  name: string
  value: number
  color: string
  payload: ChartDataPoint
}

interface CustomTooltipProps {
  readonly active?: boolean
  readonly payload?: TooltipPayloadEntry[]
  readonly label?: string
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null
  const serverName = payload[0].payload.serverName
  return (
    <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl">
      <p className="text-slate-300 text-sm mb-2">{label}</p>
      {serverName && (
        <p className="text-slate-500 text-xs mb-2">{serverName}</p>
      )}
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2 text-sm">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-slate-400">{entry.name}:</span>
          <span className="font-medium text-slate-200">
            {entry.value} {entry.name === 'Ping' ? 'ms' : 'Mbps'}
          </span>
        </div>
      ))}
    </div>
  )
}

export function SpeedChart({ data }: SpeedChartProps) {
  const chartData = data
    .slice()
    .reverse()
    .map((d) => ({
      time: new Date(d.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      }),
      Download: Number(d.download_mbps.toFixed(1)),
      Upload: Number(d.upload_mbps.toFixed(1)),
      Ping: Number(d.ping_ms.toFixed(1)),
      serverName: d.server_name,
    }))

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis
            dataKey="time"
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            dy={10}
          />
          <YAxis
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            dx={-10}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ paddingTop: '20px' }} />
          <Line
            type="monotone"
            dataKey="Download"
            stroke="#22d3ee"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 5, fill: '#22d3ee', stroke: '#0f172a', strokeWidth: 2 }}
          />
          <Line
            type="monotone"
            dataKey="Upload"
            stroke="#a78bfa"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 5, fill: '#a78bfa', stroke: '#0f172a', strokeWidth: 2 }}
          />
          <Line
            type="monotone"
            dataKey="Ping"
            stroke="#fbbf24"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 5, fill: '#fbbf24', stroke: '#0f172a', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
