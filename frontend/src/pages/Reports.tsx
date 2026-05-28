import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
  EyeOff,
  FileText,
  Filter,
  X,
} from 'lucide-react'
import { api } from '@/lib/api'
import type { ResultsFilter } from '@/lib/api'
import type { SpeedResult } from '@/types'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 25

type ColumnId =
  | 'timestamp'
  | 'download_mbps'
  | 'upload_mbps'
  | 'ping_ms'
  | 'jitter_ms'
  | 'isp_name'
  | 'server_name'
  | 'server_location'
  | 'note'

interface ColumnDef {
  id: ColumnId
  label: string
  defaultVisible: boolean
}

const COLUMNS: ColumnDef[] = [
  { id: 'timestamp', label: 'Date & Time', defaultVisible: true },
  { id: 'download_mbps', label: 'Download (Mbps)', defaultVisible: true },
  { id: 'upload_mbps', label: 'Upload (Mbps)', defaultVisible: true },
  { id: 'ping_ms', label: 'Ping (ms)', defaultVisible: true },
  { id: 'jitter_ms', label: 'Jitter (ms)', defaultVisible: true },
  { id: 'isp_name', label: 'ISP', defaultVisible: true },
  { id: 'server_name', label: 'Server', defaultVisible: true },
  { id: 'server_location', label: 'Location', defaultVisible: false },
  { id: 'note', label: 'Note', defaultVisible: false },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface FilterState {
  dateFrom: string
  dateTo: string
  minDownload: string
  maxDownload: string
  minUpload: string
  maxUpload: string
  maxPing: string
  server: string
  isp: string
}

const EMPTY_FILTERS: FilterState = {
  dateFrom: '',
  dateTo: '',
  minDownload: '',
  maxDownload: '',
  minUpload: '',
  maxUpload: '',
  maxPing: '',
  server: '',
  isp: '',
}

function activeCount(f: FilterState): number {
  return Object.values(f).filter(Boolean).length
}

function buildApiFilter(f: FilterState, page: number): ResultsFilter {
  const filter: ResultsFilter = { page, pageSize: PAGE_SIZE }
  if (f.dateFrom) filter.dateFrom = f.dateFrom
  if (f.dateTo) filter.dateTo = f.dateTo
  if (f.minDownload !== '') filter.minDownload = Number(f.minDownload)
  if (f.maxDownload !== '') filter.maxDownload = Number(f.maxDownload)
  if (f.minUpload !== '') filter.minUpload = Number(f.minUpload)
  if (f.maxUpload !== '') filter.maxUpload = Number(f.maxUpload)
  if (f.maxPing !== '') filter.maxPing = Number(f.maxPing)
  if (f.server) filter.server = f.server
  if (f.isp) filter.isp = f.isp
  return filter
}

function formatCell(row: SpeedResult, col: ColumnId): string {
  switch (col) {
    case 'timestamp':
      return new Date(row.timestamp).toLocaleString()
    case 'download_mbps':
      return `${row.download_mbps.toFixed(1)} Mbps`
    case 'upload_mbps':
      return `${row.upload_mbps.toFixed(1)} Mbps`
    case 'ping_ms':
      return `${row.ping_ms.toFixed(1)} ms`
    case 'jitter_ms':
      return row.jitter_ms == null ? '—' : `${row.jitter_ms.toFixed(1)} ms`
    case 'isp_name':
      return row.isp_name ?? '—'
    case 'server_name':
      return row.server_name
    case 'server_location':
      return row.server_location
    case 'note':
      return row.note ?? ''
    default:
      return ''
  }
}

function cellClass(col: ColumnId): string {
  switch (col) {
    case 'download_mbps':
      return 'text-cyan-400 font-medium'
    case 'upload_mbps':
      return 'text-violet-400 font-medium'
    case 'ping_ms':
      return 'text-amber-400 font-medium'
    case 'jitter_ms':
      return 'text-emerald-400 font-medium'
    default:
      return 'text-slate-700 dark:text-slate-300'
  }
}

// ---------------------------------------------------------------------------
// CSV export helper — fetches ALL matching results and triggers download
// ---------------------------------------------------------------------------

async function exportToCsv(filters: FilterState, visibleCols: ColumnId[]) {
  const allRows: SpeedResult[] = []
  let page = 1
  let total = Infinity
  while (allRows.length < total) {
    const result = await api.getResultsFiltered(buildApiFilter(filters, page))
    total = result.total
    allRows.push(...result.results)
    if (allRows.length >= total) break
    page++
  }

  const headers = COLUMNS.filter((c) => visibleCols.includes(c.id)).map((c) => c.label)
  const rows = allRows.map((row) =>
    COLUMNS.filter((c) => visibleCols.includes(c.id)).map((c) => {
      const raw = row[c.id as keyof SpeedResult]
      const val = raw == null ? '' : String(raw)
      return val.includes(',') || val.includes('"') ? `"${val.replaceAll('"', '""')}"` : val
    })
  )

  const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `hermes-report-${new Date().toISOString().split('T')[0]}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ---------------------------------------------------------------------------
// FilterPanel
// ---------------------------------------------------------------------------

interface FilterPanelProps {
  readonly filters: FilterState
  readonly servers: string[]
  readonly isps: string[]
  readonly onChange: (f: FilterState) => void
  readonly onClear: () => void
}

const inputClass =
  'w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500'

function FilterPanel({ filters, servers, isps, onChange, onClear }: FilterPanelProps) {
  return (
    <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-slate-400" />
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Filters</span>
          {activeCount(filters) > 0 && (
            <span className="text-xs font-semibold bg-cyan-500 text-white rounded-full w-4 h-4 flex items-center justify-center leading-none">
              {activeCount(filters)}
            </span>
          )}
        </div>
        {activeCount(filters) > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            <X size={12} />
            Clear all
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {/* Date range */}
        <div className="flex flex-col gap-1">
          <label htmlFor="rpt-date-from" className="text-xs text-slate-500 dark:text-slate-400">From</label>
          <input
            id="rpt-date-from"
            type="date"
            value={filters.dateFrom}
            max={filters.dateTo || undefined}
            onChange={(e) => onChange({ ...filters, dateFrom: e.target.value })}
            className={inputClass}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="rpt-date-to" className="text-xs text-slate-500 dark:text-slate-400">To</label>
          <input
            id="rpt-date-to"
            type="date"
            value={filters.dateTo}
            min={filters.dateFrom || undefined}
            onChange={(e) => onChange({ ...filters, dateTo: e.target.value })}
            className={inputClass}
          />
        </div>

        {/* Download range */}
        <div className="flex flex-col gap-1">
          <label htmlFor="rpt-min-dl" className="text-xs text-slate-500 dark:text-slate-400">Min Download (Mbps)</label>
          <input
            id="rpt-min-dl"
            type="number"
            min={0}
            step={1}
            placeholder="e.g. 50"
            value={filters.minDownload}
            onChange={(e) => onChange({ ...filters, minDownload: e.target.value })}
            className={inputClass}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="rpt-max-dl" className="text-xs text-slate-500 dark:text-slate-400">Max Download (Mbps)</label>
          <input
            id="rpt-max-dl"
            type="number"
            min={0}
            step={1}
            placeholder="e.g. 500"
            value={filters.maxDownload}
            onChange={(e) => onChange({ ...filters, maxDownload: e.target.value })}
            className={inputClass}
          />
        </div>

        {/* Upload range */}
        <div className="flex flex-col gap-1">
          <label htmlFor="rpt-min-ul" className="text-xs text-slate-500 dark:text-slate-400">Min Upload (Mbps)</label>
          <input
            id="rpt-min-ul"
            type="number"
            min={0}
            step={1}
            placeholder="e.g. 10"
            value={filters.minUpload}
            onChange={(e) => onChange({ ...filters, minUpload: e.target.value })}
            className={inputClass}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="rpt-max-ul" className="text-xs text-slate-500 dark:text-slate-400">Max Upload (Mbps)</label>
          <input
            id="rpt-max-ul"
            type="number"
            min={0}
            step={1}
            placeholder="e.g. 200"
            value={filters.maxUpload}
            onChange={(e) => onChange({ ...filters, maxUpload: e.target.value })}
            className={inputClass}
          />
        </div>

        {/* Max ping */}
        <div className="flex flex-col gap-1">
          <label htmlFor="rpt-max-ping" className="text-xs text-slate-500 dark:text-slate-400">Max Ping (ms)</label>
          <input
            id="rpt-max-ping"
            type="number"
            min={0}
            step={1}
            placeholder="e.g. 100"
            value={filters.maxPing}
            onChange={(e) => onChange({ ...filters, maxPing: e.target.value })}
            className={inputClass}
          />
        </div>

        {/* Server */}
        <div className="flex flex-col gap-1">
          <label htmlFor="rpt-server" className="text-xs text-slate-500 dark:text-slate-400">Server</label>
          <select
            id="rpt-server"
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

        {/* ISP */}
        {isps.length > 0 && (
          <div className="flex flex-col gap-1">
            <label htmlFor="rpt-isp" className="text-xs text-slate-500 dark:text-slate-400">ISP</label>
            <select
              id="rpt-isp"
              value={filters.isp}
              onChange={(e) => onChange({ ...filters, isp: e.target.value })}
              className={inputClass}
            >
              <option value="">All ISPs</option>
              {isps.map((i) => (
                <option key={i} value={i}>{i}</option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ColumnToggle panel
// ---------------------------------------------------------------------------

interface ColumnTogglePanelProps {
  readonly visibleCols: ColumnId[]
  readonly onToggle: (id: ColumnId) => void
}

function ColumnTogglePanel({ visibleCols, onToggle }: ColumnTogglePanelProps) {
  return (
    <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <Eye size={14} className="text-slate-400" />
        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Report Columns</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {COLUMNS.map((col) => {
          const visible = visibleCols.includes(col.id)
          return (
            <button
              key={col.id}
              type="button"
              onClick={() => onToggle(col.id)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                visible
                  ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
                  : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400'
              }`}
            >
              {visible ? <Eye size={11} /> : <EyeOff size={11} />}
              {col.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Reports page
// ---------------------------------------------------------------------------

export function Reports() {
  const [results, setResults] = useState<SpeedResult[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)
  const [servers, setServers] = useState<string[]>([])
  const [isps, setIsps] = useState<string[]>([])
  const [visibleCols, setVisibleCols] = useState<ColumnId[]>(
    COLUMNS.filter((c) => c.defaultVisible).map((c) => c.id)
  )
  const [showColumns, setShowColumns] = useState(false)

  const fetchResults = useCallback(async (currentPage: number, f: FilterState) => {
    setLoading(true)
    try {
      const data = await api.getResultsFiltered(buildApiFilter(f, currentPage))
      setResults(data.results)
      setTotal(data.total)
    } catch {
      setResults([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [])

  // Load dropdown options once on mount (from first large batch)
  useEffect(() => {
    api.getResultsFiltered({ pageSize: 500 }).then((p) => {
      setServers(
        [...new Set(p.results.map((r) => r.server_name))].sort((a, b) => a.localeCompare(b))
      )
      setIsps(
        [...new Set(p.results.map((r) => r.isp_name ?? '').filter(Boolean))].sort((a, b) =>
          a.localeCompare(b)
        )
      )
    }).catch(() => null)
  }, [])

  useEffect(() => {
    void fetchResults(page, filters)
  }, [fetchResults, page, filters])

  const handleFilterChange = (f: FilterState) => {
    setFilters(f)
    setPage(1)
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      await exportToCsv(filters, visibleCols)
    } finally {
      setExporting(false)
    }
  }

  const toggleCol = (id: ColumnId) => {
    setVisibleCols((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    )
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const activeFilters = activeCount(filters)

  const orderedVisible = COLUMNS.filter((c) => visibleCols.includes(c.id))

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Reports</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
            Filter speed test history and export a custom report
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowColumns((v) => !v)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              showColumns
                ? 'bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            <EyeOff size={15} />
            <span className="hidden sm:inline">Columns</span>
          </button>
          <button
            type="button"
            onClick={() => void handleExport()}
            disabled={exporting || total === 0}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              exporting || total === 0
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed'
                : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-500/20'
            }`}
          >
            <Download size={15} />
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
        </div>
      </div>

      {/* Filter panel */}
      <FilterPanel
        filters={filters}
        servers={servers}
        isps={isps}
        onChange={handleFilterChange}
        onClear={() => handleFilterChange(EMPTY_FILTERS)}
      />

      {/* Column visibility panel */}
      {showColumns && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="overflow-hidden"
        >
          <ColumnTogglePanel visibleCols={visibleCols} onToggle={toggleCol} />
        </motion.div>
      )}

      {/* Results table */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden">
        {loading && (
          <div className="p-12 text-center">
            <div className="inline-block w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {!loading && results.length === 0 ? (
          <div className="py-16 text-center text-slate-500 dark:text-slate-400">
            <FileText size={40} className="mx-auto mb-3 opacity-30" />
            <p>No results found{activeFilters > 0 ? ' for the selected filters' : ''}.</p>
            {activeFilters > 0 && (
              <button
                type="button"
                onClick={() => handleFilterChange(EMPTY_FILTERS)}
                className="mt-2 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60">
                  {orderedVisible.map((col) => (
                    <th
                      key={col.id}
                      className="text-left py-3 px-4 text-slate-500 dark:text-slate-400 font-medium whitespace-nowrap"
                    >
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
                {results.map((row) => (
                  <tr
                    key={row.id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
                  >
                    {orderedVisible.map((col) => (
                      <td
                        key={col.id}
                        className={`py-3 px-4 whitespace-nowrap ${cellClass(col.id)}`}
                      >
                        {formatCell(row, col.id)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loading && total > PAGE_SIZE && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-md text-slate-500 hover:text-slate-700 hover:bg-slate-200/70 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-xs text-slate-500 dark:text-slate-400 px-2">
                {page} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1.5 rounded-md text-slate-500 hover:text-slate-700 hover:bg-slate-200/70 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
        {!loading && total > 0 && total <= PAGE_SIZE && (
          <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {total} result{total === 1 ? '' : 's'}
            </span>
          </div>
        )}
      </div>
    </motion.div>
  )
}
