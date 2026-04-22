import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, Download } from 'lucide-react'
import type { SpeedResult } from '@/types'

interface ResultsTableProps {
  data: SpeedResult[]
}

export function ResultsTable({ data }: ResultsTableProps) {
  const [open, setOpen] = useState(false)

  const downloadCSV = (e: React.MouseEvent) => {
    e.stopPropagation()
    const headers = [
      'Timestamp',
      'Download (Mbps)',
      'Upload (Mbps)',
      'Ping (ms)',
      'Jitter (ms)',
      'ISP',
      'Server',
    ]
    const rows = data.map((d) => [
      d.timestamp,
      d.download_mbps,
      d.upload_mbps,
      d.ping_ms,
      d.jitter_ms ?? '',
      `"${d.isp_name ?? ''}"`,
      `"${d.server_name}"`,
    ])
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `hermes-results-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="border border-slate-800 rounded-xl bg-slate-900/30 overflow-hidden">
      <div
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-800/30 transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-2">
          <h3 className="font-medium text-slate-200">Result Log</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
            {data.length} entries
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={downloadCSV}
            className="flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300 transition-colors px-3 py-1.5 rounded-md bg-cyan-500/10 hover:bg-cyan-500/20"
          >
            <Download size={15} />
            <span className="hidden sm:inline">Export CSV</span>
          </button>
          {open ? (
            <ChevronUp size={18} className="text-slate-500" />
          ) : (
            <ChevronDown size={18} className="text-slate-500" />
          )}
        </div>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="overflow-x-auto border-t border-slate-800 max-h-96">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-slate-400 uppercase bg-slate-900/50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 font-medium">Date & Time</th>
                    <th className="px-4 py-3 font-medium">Download</th>
                    <th className="px-4 py-3 font-medium">Upload</th>
                    <th className="px-4 py-3 font-medium">Ping</th>
                    <th className="px-4 py-3 font-medium">Jitter</th>
                    <th className="px-4 py-3 font-medium">ISP</th>
                    <th className="px-4 py-3 font-medium">Server</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {data.map((row) => (
                    <tr
                      key={row.id}
                      className="hover:bg-slate-800/20 transition-colors"
                    >
                      <td className="px-4 py-3 text-slate-300 whitespace-nowrap">
                        {new Date(row.timestamp).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-cyan-400 font-medium">
                        {row.download_mbps.toFixed(1)} Mbps
                      </td>
                      <td className="px-4 py-3 text-violet-400 font-medium">
                        {row.upload_mbps.toFixed(1)} Mbps
                      </td>
                      <td className="px-4 py-3 text-amber-400 font-medium">
                        {row.ping_ms.toFixed(1)} ms
                      </td>
                      <td className="px-4 py-3 text-emerald-400 font-medium">
                        {row.jitter_ms != null ? `${row.jitter_ms.toFixed(1)} ms` : '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-400 truncate max-w-[120px]">
                        {row.isp_name ?? '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-400 truncate max-w-[140px]">
                        {row.server_name}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
