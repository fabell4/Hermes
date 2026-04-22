import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Download, Upload, Activity, Wifi } from 'lucide-react'
import type { SpeedResult } from '@/types'

interface SpeedGaugeProps {
  readonly isTesting: boolean
  readonly latest: SpeedResult | null
}

function randomBetween(min: number, max: number) {
  return min + Math.random() * (max - min) // NOSONAR — UI animation only, not used for security or crypto
}

export function SpeedGauge({ isTesting, latest }: SpeedGaugeProps) {
  const [animated, setAnimated] = useState({
    download: 0,
    upload: 0,
    ping: 0,
    jitter: 0,
  })

  // Animate random values while a test is running
  useEffect(() => {
    if (!isTesting) return
    const id = setInterval(() => {
      setAnimated({
        download: randomBetween(10, 400),
        upload: randomBetween(5, 150),
        ping: randomBetween(5, 80),
        jitter: randomBetween(0.5, 15),
      })
    }, 150)
    return () => clearInterval(id)
  }, [isTesting])

  const display = isTesting
    ? animated
    : {
        download: latest?.download_mbps ?? 0,
        upload: latest?.upload_mbps ?? 0,
        ping: latest?.ping_ms ?? 0,
        jitter: latest?.jitter_ms ?? 0,
      }

  const metrics = [
    {
      label: 'Download',
      value: display.download,
      unit: 'Mbps',
      icon: Download,
      color: 'text-cyan-400',
      bg: 'bg-cyan-500/10',
      border: 'border-cyan-500/20',
    },
    {
      label: 'Upload',
      value: display.upload,
      unit: 'Mbps',
      icon: Upload,
      color: 'text-violet-400',
      bg: 'bg-violet-500/10',
      border: 'border-violet-500/20',
    },
    {
      label: 'Ping',
      value: display.ping,
      unit: 'ms',
      icon: Activity,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
    },
    {
      label: 'Jitter',
      value: display.jitter,
      unit: 'ms',
      icon: Wifi,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {metrics.map((metric, i) => (
        <motion.div
          key={metric.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.08 }}
          className={`relative overflow-hidden rounded-2xl border ${metric.border} bg-slate-900/50 p-5 flex flex-col items-center justify-center text-center`}
        >
          <div className={`absolute top-0 left-0 w-full h-0.5 ${metric.bg}`} />
          <div className={`p-2.5 rounded-full ${metric.bg} ${metric.color} mb-3`}>
            <metric.icon size={20} />
          </div>
          <div className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1">
            {metric.label}
          </div>
          <div className="flex items-baseline gap-1">
            <span
              className={`text-3xl md:text-4xl font-bold tracking-tighter ${
                isTesting ? 'animate-pulse' : ''
              } ${metric.color}`}
            >
              {metric.value.toFixed(1)}
            </span>
            <span className="text-slate-500 text-sm font-medium">
              {metric.unit}
            </span>
          </div>
        </motion.div>
      ))}
    </div>
  )
}
