import { useState, useRef } from 'react'
import { motion, AnimatePresence, Reorder } from 'framer-motion'
import { CalendarClock, Play, Activity, AlertCircle, LayoutDashboard, GripVertical, Eye, EyeOff, RotateCcw } from 'lucide-react'
import { useHermes } from '@/hooks/useHermes'
import { useDashboardConfig } from '@/hooks/useDashboardConfig'
import type { MetricId, SectionId } from '@/hooks/useDashboardConfig'
import { SpeedGauge } from '@/components/SpeedGauge'
import { SpeedChart } from '@/components/SpeedChart'
import { ResultsTable } from '@/components/ResultsTable'
import { CountdownTimer } from '@/components/CountdownTimer'
import { ChartExportButton } from '@/components/ChartExportButton'

// ---------------------------------------------------------------------------
// Metric labels for the customize panel
// ---------------------------------------------------------------------------
const METRIC_LABELS: Record<MetricId, string> = {
  Download: 'Download',
  Upload: 'Upload',
  Ping: 'Ping',
  Jitter: 'Jitter',
}

const SECTION_LABELS: Record<SectionId, string> = {
  chart: 'Performance History',
  resultLog: 'Result Log',
}

// ---------------------------------------------------------------------------
// CustomizePanel
// ---------------------------------------------------------------------------

interface CustomizePanelProps {
  readonly metricOrder: MetricId[]
  readonly hiddenMetrics: MetricId[]
  readonly hiddenSections: SectionId[]
  readonly onReorder: (order: MetricId[]) => void
  readonly onToggleMetric: (id: MetricId) => void
  readonly onToggleSection: (id: SectionId) => void
  readonly onReset: () => void
}

function CustomizePanel({
  metricOrder,
  hiddenMetrics,
  hiddenSections,
  onReorder,
  onToggleMetric,
  onToggleSection,
  onReset,
}: CustomizePanelProps) {
  return (
    <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-5">
      {/* Metric cards */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
          Metric Cards — drag to reorder
        </p>
        <Reorder.Group
          axis="y"
          values={metricOrder}
          onReorder={onReorder}
          className="space-y-2"
          as="ul"
        >
          {metricOrder.map((id) => {
            const isHidden = hiddenMetrics.includes(id)
            return (
              <Reorder.Item
                key={id}
                value={id}
                as="li"
                className={`flex items-center gap-3 px-3 py-2 rounded-lg border transition-colors cursor-grab active:cursor-grabbing select-none ${
                  isHidden
                    ? 'border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/30 opacity-50'
                    : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50'
                }`}
              >
                <GripVertical size={15} className="text-slate-400 dark:text-slate-500 shrink-0" />
                <span className={`text-sm flex-1 font-medium ${isHidden ? 'text-slate-400 dark:text-slate-500' : 'text-slate-700 dark:text-slate-300'}`}>
                  {METRIC_LABELS[id]}
                </span>
                <button
                  type="button"
                  onClick={() => onToggleMetric(id)}
                  aria-label={isHidden ? `Show ${METRIC_LABELS[id]}` : `Hide ${METRIC_LABELS[id]}`}
                  className="text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
                >
                  {isHidden ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </Reorder.Item>
            )
          })}
        </Reorder.Group>
      </div>

      {/* Sections */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
          Sections
        </p>
        <div className="space-y-2">
          {(['chart', 'resultLog'] as SectionId[]).map((id) => {
            const isHidden = hiddenSections.includes(id)
            return (
              <div
                key={id}
                className="flex items-center justify-between px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50"
              >
                <span className={`text-sm font-medium ${isHidden ? 'text-slate-400 dark:text-slate-500' : 'text-slate-700 dark:text-slate-300'}`}>
                  {SECTION_LABELS[id]}
                </span>
                <button
                  type="button"
                  onClick={() => onToggleSection(id)}
                  aria-label={isHidden ? `Show ${SECTION_LABELS[id]}` : `Hide ${SECTION_LABELS[id]}`}
                  className="text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
                >
                  {isHidden ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {/* Reset */}
      <div className="flex justify-end pt-1 border-t border-slate-200 dark:border-slate-800">
        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
        >
          <RotateCcw size={12} />
          Reset to defaults
        </button>
      </div>
    </div>
  )
}

export function Dashboard() {
  const { results, latest, health, loading, isTesting, error, runTest, config: runtimeConfig } =
    useHermes()
  const { config, setMetricOrder, toggleMetric, toggleSection, reset } = useDashboardConfig()
  const [customizeOpen, setCustomizeOpen] = useState(false)
  const chartRef = useRef<HTMLDivElement>(null)

  const showChart = !config.hiddenSections.includes('chart')
  const showResultLog = !config.hiddenSections.includes('resultLog')

  // Compute whether scheduled tests are currently paused by the test window
  const tw = runtimeConfig?.test_window
  const outsideTestWindow: boolean = tw?.enabled
    ? (() => {
        const hour = new Date().getUTCHours()
        const { start_hour, end_hour } = tw
        if (start_hour < end_hour) return !(start_hour <= hour && hour < end_hour)
        return !(hour >= start_hour || hour < end_hour)
      })()
    : false
  const startLabel = tw ? String(tw.start_hour).padStart(2, '0') + ':00' : ''
  let endLabel = ''
  if (tw) {
    endLabel = tw.end_hour === 24 ? '24:00' : String(tw.end_hour).padStart(2, '0') + ':00'
  }
  const windowBannerText = `Scheduled tests paused \u2014 outside test window (${startLabel}\u2013${endLabel} UTC). Manual \u201CRun Now\u201D tests still work.`

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Dashboard</h1>
            {isTesting && (
              <span className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium">
                <Activity size={12} className="animate-spin" />
                Test Running
              </span>
            )}
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
            {(() => {
              const lastRunText = health?.last_run
                ? new Date(health.last_run).toLocaleString()
                : 'never'
              return health?.status === 'ok'
                ? `Scheduler running · last run ${lastRunText}`
                : 'Connecting to Hermes…'
            })()}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCustomizeOpen((o) => !o)}
            aria-label="Customize dashboard"
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              customizeOpen
                ? 'bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            <LayoutDashboard size={16} />
            <span className="hidden sm:inline">Customize</span>
          </button>
          <CountdownTimer nextRun={health?.next_run ?? null} />
          <button
            onClick={runTest}
            disabled={isTesting || loading}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              isTesting || loading
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed'
                : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-500/20'
            }`}
          >
            {isTesting ? (
              <Activity size={17} className="animate-pulse" />
            ) : (
              <Play size={17} className="fill-current" />
            )}
            {isTesting ? 'Testing…' : 'Run Test'}
          </button>
        </div>
      </div>

      {/* Test window notice */}
      <AnimatePresence>
        {outsideTestWindow && tw && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-sm">
              <CalendarClock size={16} className="shrink-0" />
              <span>{windowBannerText}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Customize panel */}
      <AnimatePresence>
        {customizeOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <CustomizePanel
              metricOrder={config.metricOrder}
              hiddenMetrics={config.hiddenMetrics}
              hiddenSections={config.hiddenSections}
              onReorder={setMetricOrder}
              onToggleMetric={toggleMetric}
              onToggleSection={toggleSection}
              onReset={reset}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle size={16} className="shrink-0" />
          {error}
        </div>
      )}

      {/* Metric cards */}
      <SpeedGauge
        isTesting={isTesting}
        latest={latest}
        metricOrder={config.metricOrder}
        hiddenMetrics={config.hiddenMetrics}
      />

      {/* Chart */}
      {results.length > 0 && showChart && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 md:p-6"
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">
              Performance History
            </h2>
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {results.length} samples
              </span>
              <ChartExportButton
                containerRef={chartRef}
                filename="hermes-performance-history"
              />
            </div>
          </div>
          <div ref={chartRef}>
            <SpeedChart data={results} />
          </div>
        </motion.div>
      )}

      {/* Results table */}
      {results.length > 0 && showResultLog && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
        >
          <ResultsTable data={results} />
        </motion.div>
      )}

      {/* Empty state */}
      {!loading && results.length === 0 && !error && (
        <div className="text-center py-20 text-slate-500">
          <Activity size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-lg">No results yet.</p>
          <p className="text-sm mt-1">
            Press <span className="text-cyan-500 dark:text-cyan-400 font-medium">Run Test</span> to
            take your first measurement.
          </p>
        </div>
      )}
    </motion.div>
  )
}
