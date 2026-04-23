import { motion } from 'framer-motion'
import { Play, Activity, AlertCircle } from 'lucide-react'
import { useHermes } from '@/hooks/useHermes'
import { SpeedGauge } from '@/components/SpeedGauge'
import { SpeedChart } from '@/components/SpeedChart'
import { ResultsTable } from '@/components/ResultsTable'
import { CountdownTimer } from '@/components/CountdownTimer'

export function Dashboard() {
  const { results, latest, health, loading, isTesting, error, runTest } =
    useHermes()

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
            <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>
            {isTesting && (
              <span className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium">
                <Activity size={12} className="animate-spin" />
                Test Running
              </span>
            )}
          </div>
          <p className="text-slate-400 text-sm mt-0.5">
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
          <CountdownTimer nextRun={health?.next_run ?? null} />
          <button
            onClick={runTest}
            disabled={isTesting || loading}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              isTesting || loading
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
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

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle size={16} className="shrink-0" />
          {error}
        </div>
      )}

      {/* Metric cards */}
      <SpeedGauge isTesting={isTesting} latest={latest} />

      {/* Chart */}
      {results.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 md:p-6"
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-slate-200">
              Performance History
            </h2>
            <span className="text-sm text-slate-400">
              {results.length} samples
            </span>
          </div>
          <SpeedChart data={results} />
        </motion.div>
      )}

      {/* Results table */}
      {results.length > 0 && (
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
            Press <span className="text-cyan-400 font-medium">Run Test</span> to
            take your first measurement.
          </p>
        </div>
      )}
    </motion.div>
  )
}
