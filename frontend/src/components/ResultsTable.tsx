import React, { useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, Download, Pencil, SlidersHorizontal, X } from 'lucide-react'
import type { SpeedResult } from '@/types'
import { api } from '@/lib/api'

// ---------------------------------------------------------------------------
// FilterBar
// ---------------------------------------------------------------------------

interface FilterState {
  dateFrom: string
  dateTo: string
  minDownload: string
  server: string
}

const EMPTY_FILTERS: FilterState = { dateFrom: '', dateTo: '', minDownload: '', server: '' }

function activeFilterCount(f: FilterState): number {
  return [f.dateFrom, f.dateTo, f.minDownload, f.server].filter(Boolean).length
}

interface FilterBarProps {
  readonly filters: FilterState
  readonly servers: string[]
  readonly onChange: (f: FilterState) => void
  readonly onClear: () => void
}

function FilterBar({ filters, servers, onChange, onClear }: FilterBarProps) {
  const inputClass =
    'w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500'

  return (
    <div className="px-4 pb-3 grid grid-cols-2 sm:grid-cols-4 gap-3 border-b border-slate-200 dark:border-slate-800">
      <div>
        <label htmlFor="filter-date-from" className="block text-xs text-slate-500 dark:text-slate-400 mb-1">From</label>
        <input
          id="filter-date-from"
          type="date"
          value={filters.dateFrom}
          max={filters.dateTo || undefined}
          onChange={(e) => onChange({ ...filters, dateFrom: e.target.value })}
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="filter-date-to" className="block text-xs text-slate-500 dark:text-slate-400 mb-1">To</label>
        <input
          id="filter-date-to"
          type="date"
          value={filters.dateTo}
          min={filters.dateFrom || undefined}
          onChange={(e) => onChange({ ...filters, dateTo: e.target.value })}
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="filter-min-download" className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Min Download (Mbps)</label>
        <input
          id="filter-min-download"
          type="number"
          min={0}
          step={1}
          placeholder="e.g. 50"
          value={filters.minDownload}
          onChange={(e) => onChange({ ...filters, minDownload: e.target.value })}
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="filter-server" className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Server</label>
        <select
          id="filter-server"
          value={filters.server}
          onChange={(e) => onChange({ ...filters, server: e.target.value })}
          className={inputClass}
        >
          <option value="">All servers</option>
          {servers.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
      {activeFilterCount(filters) > 0 && (
        <div className="col-span-2 sm:col-span-4 flex justify-end">
          <button
            type="button"
            onClick={onClear}
            className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
          >
            <X size={12} />
            Clear filters
          </button>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// NoteCell — inline editable annotation for a single result row
// ---------------------------------------------------------------------------

interface NoteCellProps {
  readonly resultId: number
  readonly initialNote: string | null | undefined
}

function NoteCell({ resultId, initialNote }: NoteCellProps) {
  const [note, setNote] = useState(initialNote ?? '')
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const [hasError, setHasError] = useState(false)
  const savedRef = useRef(false)

  // Keep local note in sync when parent data refreshes (not while editing)
  useEffect(() => {
    if (!editing) setNote(initialNote ?? '')
  }, [initialNote, editing])

  const startEdit = () => {
    setDraft(note)
    setEditing(true)
    setHasError(false)
    savedRef.current = false
  }

  const save = async () => {
    if (saving || savedRef.current) return
    savedRef.current = true
    setSaving(true)
    try {
      const updated = await api.updateNote(resultId, draft.trim() || null)
      setNote(updated.note ?? '')
      setEditing(false)
    } catch {
      setHasError(true)
      savedRef.current = false
    } finally {
      setSaving(false)
    }
  }

  const cancel = () => {
    setEditing(false)
    setHasError(false)
    savedRef.current = false
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') { e.preventDefault(); void save() }
    if (e.key === 'Escape') cancel()
  }

  if (editing) {
    return (
      <input
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => void save()}
        maxLength={500}
        placeholder="Add a note…"
        className={`w-full min-w-[120px] bg-white dark:bg-slate-950 border rounded px-2 py-0.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none transition-colors ${
          hasError ? 'border-red-500 focus:border-red-400' : 'border-cyan-500 focus:border-cyan-400'
        } ${saving ? 'opacity-60' : ''}`}
      />
    )
  }

  return (
    <button
      type="button"
      onClick={startEdit}
      className="group flex items-center gap-1 text-left w-full max-w-[180px]"
      title={note || 'Click to add a note'}
    >
      {note ? (
        <>
          <span className="text-amber-500 dark:text-amber-400/80 text-xs truncate">{note}</span>
          <Pencil
            size={10}
            className="shrink-0 text-slate-400 dark:text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity"
          />
        </>
      ) : (
        <span className="text-slate-400 dark:text-slate-600 text-xs italic opacity-0 group-hover:opacity-100 transition-opacity">
          + note
        </span>
      )}
    </button>
  )
}

// ---------------------------------------------------------------------------
// ResultsTable
// ---------------------------------------------------------------------------

interface ResultsTableProps {
  readonly data: SpeedResult[]
}

export function ResultsTable({ data }: ResultsTableProps) {
  const [open, setOpen] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)

  const servers = useMemo(
    () => [...new Set(data.map((d) => d.server_name))].sort((a, b) => a.localeCompare(b)),
    [data]
  )

  const filtered = useMemo(() => {
    return data.filter((row) => {
      if (filters.dateFrom) {
        const rowDate = row.timestamp.slice(0, 10)
        if (rowDate < filters.dateFrom) return false
      }
      if (filters.dateTo) {
        const rowDate = row.timestamp.slice(0, 10)
        if (rowDate > filters.dateTo) return false
      }
      if (filters.minDownload !== '') {
        const threshold = Number.parseFloat(filters.minDownload)
        if (!Number.isNaN(threshold) && row.download_mbps < threshold) return false
      }
      if (filters.server && row.server_name !== filters.server) return false
      return true
    })
  }, [data, filters])

  const isFiltered = filtered.length < data.length
  const filterCount = activeFilterCount(filters)

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
    const rows = filtered.map((d) => [
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
    <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900/30 overflow-hidden">
      <button
        type="button"
        className="w-full p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-2">
          <h3 className="font-medium text-slate-800 dark:text-slate-200">Result Log</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
            {isFiltered ? `${filtered.length} of ${data.length}` : `${data.length}`} entries
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={(e) => { e.stopPropagation(); setShowFilters((v) => !v) }}
            className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md transition-colors ${
              filterCount > 0
                ? 'text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 bg-slate-100 dark:bg-slate-800/50 hover:bg-slate-200 dark:hover:bg-slate-700/50'
            }`}
            aria-label="Toggle filters"
          >
            <SlidersHorizontal size={14} />
            <span className="hidden sm:inline">Filters</span>
            {filterCount > 0 && (
              <span className="text-xs font-semibold bg-cyan-500 text-white rounded-full w-4 h-4 flex items-center justify-center leading-none">
                {filterCount}
              </span>
            )}
          </button>
          <button
            onClick={downloadCSV}
            className="flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300 transition-colors px-3 py-1.5 rounded-md bg-cyan-500/10 hover:bg-cyan-500/20"
          >
            <Download size={15} />
            <span className="hidden sm:inline">Export CSV</span>
          </button>
          {open ? (
            <ChevronUp size={18} className="text-slate-400 dark:text-slate-500" />
          ) : (
            <ChevronDown size={18} className="text-slate-400 dark:text-slate-500" />
          )}
        </div>
      </button>

      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="pt-3">
              <FilterBar
                filters={filters}
                servers={servers}
                onChange={setFilters}
                onClear={() => setFilters(EMPTY_FILTERS)}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="overflow-x-auto border-t border-slate-200 dark:border-slate-800 max-h-96">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-slate-500 dark:text-slate-400 uppercase bg-slate-50 dark:bg-slate-900/50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 font-medium">Date &amp; Time</th>
                    <th className="px-4 py-3 font-medium">Download</th>
                    <th className="px-4 py-3 font-medium">Upload</th>
                    <th className="px-4 py-3 font-medium">Ping</th>
                    <th className="px-4 py-3 font-medium">Jitter</th>
                    <th className="px-4 py-3 font-medium">ISP</th>
                    <th className="px-4 py-3 font-medium">Server</th>
                    <th className="px-4 py-3 font-medium">Note</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/50 dark:divide-slate-800/50">
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-sm text-slate-500 dark:text-slate-400">
                        No results match the current filters.
                      </td>
                    </tr>
                  ) : (
                    filtered.map((row) => (
                    <tr
                      key={row.id}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors"
                    >
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300 whitespace-nowrap">
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
                        {row.jitter_ms == null ? '—' : `${row.jitter_ms.toFixed(1)} ms`}
                      </td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400 truncate max-w-[120px]">
                        {row.isp_name ?? '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400 truncate max-w-[140px]">
                        {row.server_name}
                      </td>
                      <td className="px-4 py-2">
                        <NoteCell resultId={row.id} initialNote={row.note} />
                      </td>
                    </tr>
                  ))
                  )}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
