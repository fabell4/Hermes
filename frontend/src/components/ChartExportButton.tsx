import { useRef, useState, useEffect } from 'react'
import type { RefObject } from 'react'
import { Download, ChevronDown } from 'lucide-react'
import { useChartExport } from '@/hooks/useChartExport'

interface ChartExportButtonProps {
  /** Ref to the container element whose first <svg> will be captured. */
  readonly containerRef: RefObject<HTMLElement | null>
  /** Base filename (without extension) for the downloaded file. */
  readonly filename?: string
}

export function ChartExportButton({
  containerRef,
  filename = 'hermes-chart',
}: ChartExportButtonProps) {
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const { exportAs } = useChartExport(containerRef)

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!open) return
    function handlePointerDown(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [open])

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label="Export chart"
        aria-expanded={open}
        aria-haspopup="menu"
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-colors"
      >
        <Download size={13} />
        Export
        <ChevronDown size={11} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-1 z-20 w-28 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl py-1"
        >
          {(['png', 'svg'] as const).map((fmt) => (
            <button
              key={fmt}
              role="menuitem"
              type="button"
              onClick={() => {
                exportAs(fmt, filename)
                setOpen(false)
              }}
              className="w-full text-left px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              {fmt.toUpperCase()}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
