import { useEffect, useState } from 'react'
import { Clock } from 'lucide-react'

interface CountdownTimerProps {
  /** ISO 8601 timestamp of the next scheduled run, or null. */
  readonly nextRun: string | null
}

export function CountdownTimer({ nextRun }: CountdownTimerProps) {
  const [timeLeft, setTimeLeft] = useState(0)

  useEffect(() => {
    if (!nextRun) return
    const update = () => {
      setTimeLeft(Math.max(0, new Date(nextRun).getTime() - Date.now()))
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [nextRun])

  if (!nextRun) return null

  const minutes = Math.floor(timeLeft / 60_000)
  const seconds = Math.floor((timeLeft % 60_000) / 1000)
  const almostDue = timeLeft < 60_000

  return (
    <div className="flex items-center gap-2 text-slate-400 bg-slate-800/50 px-3 py-1.5 rounded-lg border border-slate-700/50">
      <Clock
        size={15}
        className={almostDue ? 'text-amber-400 animate-pulse' : ''}
      />
      <span className="text-sm font-mono font-medium">
        {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
      </span>
      <span className="hidden sm:inline text-xs text-slate-500">
        until next test
      </span>
    </div>
  )
}
